import sys
import taichi as ti
import numpy as np
import trimesh as tm
from functools import reduce
from config_builder import SimConfig
from WCSPH import WCSPHSolver
from DFSPH import DFSPHSolver
from scan_single_buffer import parallel_prefix_sum_inclusive_inplace

@ti.data_oriented
class ParticleSystem:
    def __init__(self, config: SimConfig, GGUI=False):
        self.cfg = config
        self.GGUI = GGUI

        # ========== Analysis space (domain) ==========
        # The analysis space is defined entirely by the config file. The object
        # is NOT normalized into this space; the object keeps its own size and is
        # only scaled by the user-specified "scale" multiplier (see load_rigid_body).
        self.domain_start = np.array(self.cfg.get_cfg("domainStart"), dtype=np.float64)
        self.domain_end = np.array(self.cfg.get_cfg("domainEnd"), dtype=np.float64)

        self.domain_size = self.domain_end - self.domain_start
        assert np.all(self.domain_size > 0.0), \
            f"domainEnd {self.domain_end.tolist()} must be strictly greater than " \
            f"domainStart {self.domain_start.tolist()} on every axis."

        self.dim = len(self.domain_size)
        assert self.dim > 1

        # Allow the domain-fit guard (recommend a scale and abort when an object
        # is larger than the analysis space) to be disabled from the config.
        self.enforce_domain_fit = self.cfg.get_cfg("enforceDomainFit")
        if self.enforce_domain_fit is None:
            self.enforce_domain_fit = True

        self.domain_start_ti = ti.Vector.field(self.dim, dtype=ti.f32, shape=())
        self.domain_start_ti[None] = ti.Vector(list(self.domain_start.astype(np.float32)))

        self.domain_end_ti = ti.Vector.field(self.dim, dtype=ti.f32, shape=())
        self.domain_end_ti[None] = ti.Vector(self.domain_end.astype(np.float32))

        # Simulation method
        self.simulation_method = self.cfg.get_cfg("simulationMethod")

        # Material
        self.material_solid = 0
        self.material_fluid = 1

        self.particle_radius = 0.01  # particle radius
        self.particle_radius = self.cfg.get_cfg("particleRadius")

        self.particle_diameter = 2 * self.particle_radius
        self.support_radius = self.particle_radius * 4.0  # support radius
        self.m_V0 = 0.8 * self.particle_diameter ** self.dim

        self.particle_num = ti.field(int, shape=())

        # Grid related properties
        self.grid_size = self.support_radius
        self.grid_num = np.ceil(self.domain_size / self.grid_size).astype(int)
        print("grid size: ", self.grid_num)
        self.padding = self.grid_size

        # All objects id and its particle num
        self.object_collection = dict()
        self.object_id_rigid_body = set()

        #========== Compute number of particles ==========#
        #### Process Fluid Blocks ####
        fluid_blocks = self.cfg.get_fluid_blocks()
        fluid_particle_num = 0
        for fluid in fluid_blocks:
            particle_num = self.compute_cube_particle_num(fluid["start"], fluid["end"])
            fluid["particleNum"] = particle_num
            self.object_collection[fluid["objectId"]] = fluid
            fluid_particle_num += particle_num

        #### Process Rigid Blocks ####
        rigid_blocks = self.cfg.get_rigid_blocks()
        rigid_particle_num = 0
        for rigid in rigid_blocks:
            particle_num = self.compute_cube_particle_num(rigid["start"], rigid["end"])
            rigid["particleNum"] = particle_num
            self.object_collection[rigid["objectId"]] = rigid
            rigid_particle_num += particle_num
        
        #### Process Rigid Bodies ####
        rigid_bodies = self.cfg.get_rigid_bodies()
        for rigid_body in rigid_bodies:
            voxelized_points_np = self.load_rigid_body(rigid_body)
            rigid_body["particleNum"] = voxelized_points_np.shape[0]
            rigid_body["voxelizedPoints"] = voxelized_points_np
            self.object_collection[rigid_body["objectId"]] = rigid_body
            rigid_particle_num += voxelized_points_np.shape[0]
        
        self.fluid_particle_num = fluid_particle_num
        self.solid_particle_num = rigid_particle_num
        self.particle_max_num = fluid_particle_num + rigid_particle_num
        self.num_rigid_bodies = len(rigid_blocks)+len(rigid_bodies)

        #### TODO: Handle the Particle Emitter ####
        # self.particle_max_num += emitted particles
        print(f"Current particle num: {self.particle_num[None]}, Particle max num: {self.particle_max_num}")

        #========== Allocate memory ==========#
        # Rigid body properties
        if self.num_rigid_bodies > 0:
            # TODO: Here we actually only need to store rigid boides, however the object id of rigid may not start from 0, so allocate center of mass for all objects
            self.rigid_rest_cm = ti.Vector.field(self.dim, dtype=float, shape=self.num_rigid_bodies + len(fluid_blocks))

        # Particle num of each grid
        n_grid = int(self.grid_num[0] * self.grid_num[1] * self.grid_num[2])
        self.grid_particles_num = ti.field(dtype=ti.i32, shape=n_grid)
        self.grid_particles_num_temp = ti.field(dtype=ti.i32, shape=n_grid)
        #self.grid_particles_num = ti.field(int, shape=int(self.grid_num[0]*self.grid_num[1]*self.grid_num[2]))
        #self.grid_particles_num_temp = ti.field(int, shape=int(self.grid_num[0]*self.grid_num[1]*self.grid_num[2]))

        self.prefix_sum_executor = ti.algorithms.PrefixSumExecutor(self.grid_particles_num.shape[0])

        # Particle related properties
        self.object_id = ti.field(dtype=int, shape=self.particle_max_num)
        self.x = ti.Vector.field(self.dim, dtype=float, shape=self.particle_max_num)
        self.x_0 = ti.Vector.field(self.dim, dtype=float, shape=self.particle_max_num)
        self.v = ti.Vector.field(self.dim, dtype=float, shape=self.particle_max_num)
        self.acceleration = ti.Vector.field(self.dim, dtype=float, shape=self.particle_max_num)
        self.m_V = ti.field(dtype=float, shape=self.particle_max_num)
        self.m = ti.field(dtype=float, shape=self.particle_max_num)
        self.density = ti.field(dtype=float, shape=self.particle_max_num)
        self.pressure = ti.field(dtype=float, shape=self.particle_max_num)
        self.material = ti.field(dtype=int, shape=self.particle_max_num)
        self.color = ti.Vector.field(3, dtype=int, shape=self.particle_max_num)
        self.is_dynamic = ti.field(dtype=int, shape=self.particle_max_num)

        if self.cfg.get_cfg("simulationMethod") == 4:
            self.dfsph_factor = ti.field(dtype=float, shape=self.particle_max_num)
            self.density_adv = ti.field(dtype=float, shape=self.particle_max_num)

        # Buffer for sort
        self.object_id_buffer = ti.field(dtype=int, shape=self.particle_max_num)
        self.x_buffer = ti.Vector.field(self.dim, dtype=float, shape=self.particle_max_num)
        self.x_0_buffer = ti.Vector.field(self.dim, dtype=float, shape=self.particle_max_num)
        self.v_buffer = ti.Vector.field(self.dim, dtype=float, shape=self.particle_max_num)
        self.acceleration_buffer = ti.Vector.field(self.dim, dtype=float, shape=self.particle_max_num)
        self.m_V_buffer = ti.field(dtype=float, shape=self.particle_max_num)
        self.m_buffer = ti.field(dtype=float, shape=self.particle_max_num)
        self.density_buffer = ti.field(dtype=float, shape=self.particle_max_num)
        self.pressure_buffer = ti.field(dtype=float, shape=self.particle_max_num)
        self.material_buffer = ti.field(dtype=int, shape=self.particle_max_num)
        self.color_buffer = ti.Vector.field(3, dtype=int, shape=self.particle_max_num)
        self.is_dynamic_buffer = ti.field(dtype=int, shape=self.particle_max_num)

        if self.cfg.get_cfg("simulationMethod") == 4:
            self.dfsph_factor_buffer = ti.field(dtype=float, shape=self.particle_max_num)
            self.density_adv_buffer = ti.field(dtype=float, shape=self.particle_max_num)

        # Grid id for each particle
        self.grid_ids = ti.field(int, shape=self.particle_max_num)
        self.grid_ids_buffer = ti.field(int, shape=self.particle_max_num)
        self.grid_ids_new = ti.field(int, shape=self.particle_max_num)

        self.x_vis_buffer = None
        if self.GGUI:
            self.x_vis_buffer = ti.Vector.field(self.dim, dtype=float, shape=self.particle_max_num)
            self.color_vis_buffer = ti.Vector.field(3, dtype=float, shape=self.particle_max_num)


        #========== Initialize particles ==========#

        # Fluid block
        for fluid in fluid_blocks:
            obj_id = fluid["objectId"]
            offset = np.array(fluid["translation"])
            start = np.array(fluid["start"]) + offset
            end = np.array(fluid["end"]) + offset
            scale = np.array(fluid["scale"])
            velocity = fluid["velocity"]
            density = fluid["density"]
            color = fluid["color"]
            self.add_cube(object_id=obj_id,
                          lower_corner=start,
                          cube_size=(end-start)*scale,
                          velocity=velocity,
                          density=density, 
                          is_dynamic=1, # enforce fluid dynamic
                          color=color,
                          material=1) # 1 indicates fluid
        
        # TODO: Handle rigid block
        # Rigid block
        for rigid in rigid_blocks:
            obj_id = rigid["objectId"]
            offset = np.array(rigid["translation"])
            start = np.array(rigid["start"]) + offset
            end = np.array(rigid["end"]) + offset
            scale = np.array(rigid["scale"])
            velocity = rigid["velocity"]
            density = rigid["density"]
            color = rigid["color"]
            is_dynamic = rigid["isDynamic"]
            self.add_cube(object_id=obj_id,
                          lower_corner=start,
                          cube_size=(end-start)*scale,
                          velocity=velocity,
                          density=density, 
                          is_dynamic=is_dynamic,
                          color=color,
                          material=0) # 1 indicates solid

        # Rigid bodies
        for rigid_body in rigid_bodies:
            obj_id = rigid_body["objectId"]
            self.object_id_rigid_body.add(obj_id)
            num_particles_obj = rigid_body["particleNum"]
            voxelized_points_np = rigid_body["voxelizedPoints"]
            is_dynamic = rigid_body["isDynamic"]
            if is_dynamic:
                velocity = np.array(rigid_body["velocity"], dtype=np.float32)
            else:
                velocity = np.array([0.0 for _ in range(self.dim)], dtype=np.float32)
            density = rigid_body["density"]
            color = np.array(rigid_body["color"], dtype=np.int32)
            self.add_particles(obj_id,
                               num_particles_obj,
                               np.array(voxelized_points_np, dtype=np.float32), # position
                               np.stack([velocity for _ in range(num_particles_obj)]), # velocity
                               density * np.ones(num_particles_obj, dtype=np.float32), # density
                               np.zeros(num_particles_obj, dtype=np.float32), # pressure
                               np.array([0 for _ in range(num_particles_obj)], dtype=np.int32), # material is solid
                               is_dynamic * np.ones(num_particles_obj, dtype=np.int32), # is_dynamic
                               np.stack([color for _ in range(num_particles_obj)])) # color
    

    def build_solver(self):
        solver_type = self.cfg.get_cfg("simulationMethod")
        if solver_type == 0:
            return WCSPHSolver(self)
        elif solver_type == 4:
            return DFSPHSolver(self)
        else:
            raise NotImplementedError(f"Solver type {solver_type} has not been implemented.")

    @ti.func
    def add_particle(self, p, obj_id, x, v, density, pressure, material, is_dynamic, color):
        self.object_id[p] = obj_id
        self.x[p] = x
        self.x_0[p] = x
        self.v[p] = v
        self.density[p] = density
        self.m_V[p] = self.m_V0
        self.m[p] = self.m_V0 * density
        self.pressure[p] = pressure
        self.material[p] = material
        self.is_dynamic[p] = is_dynamic
        self.color[p] = color
    
    def add_particles(self,
                      object_id: int,
                      new_particles_num: int,
                      new_particles_positions: ti.types.ndarray(),
                      new_particles_velocity: ti.types.ndarray(),
                      new_particle_density: ti.types.ndarray(),
                      new_particle_pressure: ti.types.ndarray(),
                      new_particles_material: ti.types.ndarray(),
                      new_particles_is_dynamic: ti.types.ndarray(),
                      new_particles_color: ti.types.ndarray()
                      ):
        
        self._add_particles(object_id,
                      new_particles_num,
                      new_particles_positions,
                      new_particles_velocity,
                      new_particle_density,
                      new_particle_pressure,
                      new_particles_material,
                      new_particles_is_dynamic,
                      new_particles_color
                      )

    @ti.kernel
    def _add_particles(self,
                      object_id: int,
                      new_particles_num: int,
                      new_particles_positions: ti.types.ndarray(),
                      new_particles_velocity: ti.types.ndarray(),
                      new_particle_density: ti.types.ndarray(),
                      new_particle_pressure: ti.types.ndarray(),
                      new_particles_material: ti.types.ndarray(),
                      new_particles_is_dynamic: ti.types.ndarray(),
                      new_particles_color: ti.types.ndarray()):
        for p in range(self.particle_num[None], self.particle_num[None] + new_particles_num):
            v = ti.Vector.zero(float, self.dim)
            x = ti.Vector.zero(float, self.dim)
            for d in ti.static(range(self.dim)):
                v[d] = new_particles_velocity[p - self.particle_num[None], d]
                x[d] = new_particles_positions[p - self.particle_num[None], d]
            self.add_particle(p, object_id, x, v,
                              new_particle_density[p - self.particle_num[None]],
                              new_particle_pressure[p - self.particle_num[None]],
                              new_particles_material[p - self.particle_num[None]],
                              new_particles_is_dynamic[p - self.particle_num[None]],
                              ti.Vector([new_particles_color[p - self.particle_num[None], i] for i in range(3)])
                              )
        self.particle_num[None] += new_particles_num


    @ti.func
    def pos_to_index(self, pos):
        rel = pos - self.domain_start_ti[None]
        idx = (rel / self.grid_size).cast(int)
    
        # clamp（必須）
        for d in ti.static(range(self.dim)):
            idx[d] = ti.max(0, ti.min(idx[d], self.grid_num[d] - 1))
    
        return idx
        #return (pos / self.grid_size).cast(int)


    @ti.func
    def flatten_grid_index(self, grid_index):
        return grid_index[0] * self.grid_num[1] * self.grid_num[2] + grid_index[1] * self.grid_num[2] + grid_index[2]
    
    @ti.func
    def get_flatten_grid_index(self, pos):
        return self.flatten_grid_index(self.pos_to_index(pos))
    

    @ti.func
    def is_static_rigid_body(self, p):
        return self.material[p] == self.material_solid and (not self.is_dynamic[p])


    @ti.func
    def is_dynamic_rigid_body(self, p):
        return self.material[p] == self.material_solid and self.is_dynamic[p]
    

    @ti.kernel
    def update_grid_id(self):
        # grid_particles_num をゼロクリア
        for I in ti.grouped(self.grid_particles_num):
            self.grid_particles_num[I] = 0
    
        pn = self.particle_num[None]
        for i in range(pn):
            grid_index = self.get_flatten_grid_index(self.x[i])
            self.grid_ids[i] = grid_index
            ti.atomic_add(self.grid_particles_num[grid_index], 1)
    
        # temp に counts をコピー（counter用）
        for I in ti.grouped(self.grid_particles_num):
            self.grid_particles_num_temp[I] = self.grid_particles_num[I]
        '''    
        for I in ti.grouped(self.grid_particles_num):
            self.grid_particles_num[I] = 0
        for I in ti.grouped(self.x):
            grid_index = self.get_flatten_grid_index(self.x[I])
            self.grid_ids[I] = grid_index
            ti.atomic_add(self.grid_particles_num[grid_index], 1)
        for I in ti.grouped(self.grid_particles_num):
            self.grid_particles_num_temp[I] = self.grid_particles_num[I]
        '''
    @ti.kernel
    def counting_sort(self):
        pn = self.particle_num[None]
    
        # 1) new_index 計算
        for i in range(pn):
            I = pn - 1 - i
            gid = self.grid_ids[I]
    
            base_offset = 0
            if gid - 1 >= 0:
                base_offset = self.grid_particles_num[gid - 1]  # prefix（累積）
    
            self.grid_ids_new[I] = ti.atomic_sub(self.grid_particles_num_temp[gid], 1) - 1 + base_offset
    
        # 2) bufferへ散布
        for I in range(pn):
            new_index = self.grid_ids_new[I]
            self.grid_ids_buffer[new_index] = self.grid_ids[I]
            self.object_id_buffer[new_index] = self.object_id[I]
            self.x_0_buffer[new_index] = self.x_0[I]
            self.x_buffer[new_index] = self.x[I]
            self.v_buffer[new_index] = self.v[I]
            self.acceleration_buffer[new_index] = self.acceleration[I]
            self.m_V_buffer[new_index] = self.m_V[I]
            self.m_buffer[new_index] = self.m[I]
            self.density_buffer[new_index] = self.density[I]
            self.pressure_buffer[new_index] = self.pressure[I]
            self.material_buffer[new_index] = self.material[I]
            self.color_buffer[new_index] = self.color[I]
            self.is_dynamic_buffer[new_index] = self.is_dynamic[I]
    
            if ti.static(self.simulation_method == 4):
                self.dfsph_factor_buffer[new_index] = self.dfsph_factor[I]
                self.density_adv_buffer[new_index] = self.density_adv[I]
    
        # 3) buffer → 本体へ戻す
        for I in range(pn):
            self.grid_ids[I] = self.grid_ids_buffer[I]
            self.object_id[I] = self.object_id_buffer[I]
            self.x_0[I] = self.x_0_buffer[I]
            self.x[I] = self.x_buffer[I]
            self.v[I] = self.v_buffer[I]
            self.acceleration[I] = self.acceleration_buffer[I]
            self.m_V[I] = self.m_V_buffer[I]
            self.m[I] = self.m_buffer[I]
            self.density[I] = self.density_buffer[I]
            self.pressure[I] = self.pressure_buffer[I]
            self.material[I] = self.material_buffer[I]
            self.color[I] = self.color_buffer[I]
            self.is_dynamic[I] = self.is_dynamic_buffer[I]
    
            if ti.static(self.simulation_method == 4):
                self.dfsph_factor[I] = self.dfsph_factor_buffer[I]
                self.density_adv[I] = self.density_adv_buffer[I]
        '''    
        # FIXME: make it the actual particle num
        for i in range(self.particle_max_num):
            I = self.particle_max_num - 1 - i
            base_offset = 0
            if self.grid_ids[I] - 1 >= 0:
                base_offset = self.grid_particles_num[self.grid_ids[I]-1]
            self.grid_ids_new[I] = ti.atomic_sub(self.grid_particles_num_temp[self.grid_ids[I]], 1) - 1 + base_offset

        for I in ti.grouped(self.grid_ids):
            new_index = self.grid_ids_new[I]
            self.grid_ids_buffer[new_index] = self.grid_ids[I]
            self.object_id_buffer[new_index] = self.object_id[I]
            self.x_0_buffer[new_index] = self.x_0[I]
            self.x_buffer[new_index] = self.x[I]
            self.v_buffer[new_index] = self.v[I]
            self.acceleration_buffer[new_index] = self.acceleration[I]
            self.m_V_buffer[new_index] = self.m_V[I]
            self.m_buffer[new_index] = self.m[I]
            self.density_buffer[new_index] = self.density[I]
            self.pressure_buffer[new_index] = self.pressure[I]
            self.material_buffer[new_index] = self.material[I]
            self.color_buffer[new_index] = self.color[I]
            self.is_dynamic_buffer[new_index] = self.is_dynamic[I]

            if ti.static(self.simulation_method == 4):
                self.dfsph_factor_buffer[new_index] = self.dfsph_factor[I]
                self.density_adv_buffer[new_index] = self.density_adv[I]
        
        for I in ti.grouped(self.x):
            self.grid_ids[I] = self.grid_ids_buffer[I]
            self.object_id[I] = self.object_id_buffer[I]
            self.x_0[I] = self.x_0_buffer[I]
            self.x[I] = self.x_buffer[I]
            self.v[I] = self.v_buffer[I]
            self.acceleration[I] = self.acceleration_buffer[I]
            self.m_V[I] = self.m_V_buffer[I]
            self.m[I] = self.m_buffer[I]
            self.density[I] = self.density_buffer[I]
            self.pressure[I] = self.pressure_buffer[I]
            self.material[I] = self.material_buffer[I]
            self.color[I] = self.color_buffer[I]
            self.is_dynamic[I] = self.is_dynamic_buffer[I]

            if ti.static(self.simulation_method == 4):
                self.dfsph_factor[I] = self.dfsph_factor_buffer[I]
                self.density_adv[I] = self.density_adv_buffer[I]
            '''
            
    def initialize_particle_system(self):
        #self.update_grid_id()
        #self.prefix_sum_executor.run(self.grid_particles_num)
        #self.counting_sort()

        self.update_grid_id()  # ここで grid_particles_num は counts
    
        if ti.lang.impl.current_cfg().arch == ti.cpu:
            counts = self.grid_particles_num.to_numpy().astype(np.int32)
    
            # counter 用（atomic_subで減る）
            self.grid_particles_num_temp.from_numpy(counts)
    
            # prefix 用：inclusive scan（for_all_neighbors と counting_sort がこの形を期待）
            prefix = counts.copy()
            np.cumsum(prefix, out=prefix)
            self.grid_particles_num.from_numpy(prefix)
    
        else:
            # GPUは今は使わない前提（vulkan問題があるので）
            self.grid_particles_num_temp.copy_from(self.grid_particles_num)
            self.prefix_sum_executor.run(self.grid_particles_num)
    
        self.counting_sort()

    @ti.func
    def for_all_neighbors(self, p_i: int, task: ti.template(), ret: ti.template()):
        center_cell = self.pos_to_index(self.x[p_i])
    
        for offset in ti.grouped(ti.ndrange(*((-1, 2),) * self.dim)):
            cell = center_cell + offset
    
            # 3D前提の範囲チェック（超重要）
            if 0 <= cell[0] < self.grid_num[0] and 0 <= cell[1] < self.grid_num[1] and 0 <= cell[2] < self.grid_num[2]:
                grid_index = self.flatten_grid_index(cell)
    
                start = 0
                if grid_index - 1 >= 0:
                    start = self.grid_particles_num[grid_index - 1]
                end = self.grid_particles_num[grid_index]
    
                for p_j in range(start, end):
                    if p_i != p_j:
                        r = self.x[p_i] - self.x[p_j]
                        if r.dot(r) < self.support_radius * self.support_radius:
                            task(p_i, p_j, ret)

    @ti.kernel
    def copy_to_numpy(self, np_arr: ti.types.ndarray(), src_arr: ti.template()):
        for i in range(self.particle_num[None]):
            np_arr[i] = src_arr[i]
    
    def copy_to_vis_buffer(self, invisible_objects=[]):
        if len(invisible_objects) != 0:
            self.x_vis_buffer.fill(0.0)
            self.color_vis_buffer.fill(0.0)
        if self.x_vis_buffer is None or self.x is None:
            return  # 可視化バッファ無ければスキップ
        for obj_id in self.object_collection:
            if obj_id not in invisible_objects:
                self._copy_to_vis_buffer(obj_id)

    @ti.kernel
    def _copy_to_vis_buffer(self, obj_id: int):
        assert self.GGUI
        # FIXME: make it equal to actual particle num
        for i in range(self.particle_max_num):
            if self.object_id[i] == obj_id:
                self.x_vis_buffer[i] = self.x[i]
                self.color_vis_buffer[i] = self.color[i] / 255.0

    def dump(self, obj_id):
        np_object_id = self.object_id.to_numpy()
        mask = (np_object_id == obj_id).nonzero()
        np_x = self.x.to_numpy()[mask]
        np_v = self.v.to_numpy()[mask]

        return {
            'position': np_x,
            'velocity': np_v
        }
    

    def _clean_mesh(self, mesh, obj_id):
        """メッシュポリゴンデータの数値誤差対策。

        解析空間へ正規化する（＝固定サイズに押し込める）代わりに、メッシュ側の
        数値的な不正（重複頂点・退化面・NaN/Inf 頂点など）をここで除去する。
        オブジェクトの実寸は変更しない。trimesh のバージョン差を吸収するため、
        利用可能な API だけを best-effort で適用する。
        """
        # NaN / Inf を含む頂点・面を除去
        try:
            mesh.remove_infinite_values()
        except Exception:
            pass
        # 近接する重複頂点をマージ（浮動小数の微小誤差を吸収）
        try:
            mesh.merge_vertices()
        except Exception:
            pass
        # 退化面（面積ゼロ）を除去（trimesh の版により API 名が異なる）
        try:
            mesh.update_faces(mesh.nondegenerate_faces())
        except Exception:
            try:
                mesh.remove_degenerate_faces()
            except Exception:
                pass
        # 重複面・未使用頂点の除去
        for method in ("remove_duplicate_faces", "remove_unreferenced_vertices"):
            fn = getattr(mesh, method, None)
            if fn is not None:
                try:
                    fn()
                except Exception:
                    pass
        # 整合性の取れた状態へ（法線再計算など）
        try:
            mesh.process(validate=True)
        except TypeError:
            try:
                mesh.process()
            except Exception:
                pass
        except Exception:
            pass
        return mesh

    def _check_object_fits_domain(self, obj_id, current_scale, world_min, world_max):
        """scale 適用後のオブジェクト外接ボックスが解析空間に収まるか検証する。

        判定は2段階:
          1) サイズ超過: オブジェクトの外接ボックスサイズが解析空間サイズより
             大きい軸がある場合 → 推奨オブジェクト倍率（アスペクト比保持／軸別）を
             コマンドラインに出力してエラー終了する。
          2) 配置はみ出し: サイズは収まるが translation により解析空間外へはみ出す
             場合 → translation の修正を促す。
        enforceDomainFit=false の場合はいずれも警告のみで続行する。
        """
        world_min = np.asarray(world_min, dtype=np.float64)
        world_max = np.asarray(world_max, dtype=np.float64)
        extent = world_max - world_min

        over_low = self.domain_start - world_min    # >0 なら下側にはみ出し
        over_high = world_max - self.domain_end     # >0 なら上側にはみ出し
        protruding = bool(np.any(over_low > 1e-9) or np.any(over_high > 1e-9))
        if not protruding:
            return  # 解析空間に完全に収まっている

        cur_scale = np.array(current_scale, dtype=np.float64)
        if cur_scale.size == 1:
            cur_scale = np.repeat(cur_scale, self.dim)

        # 各軸で「解析空間サイズ / オブジェクトサイズ」の比。<1 の軸はサイズ超過。
        safe_extent = np.where(extent > 1e-12, extent, np.inf)
        axis_fit_ratio = self.domain_size / safe_extent
        size_exceeded = bool(np.any(axis_fit_ratio < 1.0))

        header = (
            "\n==================== OBJECT DOES NOT FIT ANALYSIS SPACE ====================\n"
            f"  RigidBody objectId : {obj_id}\n"
            f"  analysis space     : start={self.domain_start.tolist()} end={self.domain_end.tolist()} "
            f"size={np.round(self.domain_size,4).tolist()}\n"
            f"  object bbox (scale={cur_scale.tolist()} 適用後): "
            f"min={np.round(world_min,4).tolist()} max={np.round(world_max,4).tolist()} "
            f"size={np.round(extent,4).tolist()}\n"
        )

        SAFETY = 0.98  # 余白（境界にちょうど接するのを避ける）
        if size_exceeded:
            # アスペクト比を保持したまま全体を収める一様倍率
            k_uniform = SAFETY * float(np.min(axis_fit_ratio))
            recommended_uniform = cur_scale * k_uniform
            # 各軸を独立に収める倍率（既に収まっている軸は変更しない）
            per_axis_k = np.minimum(1.0, SAFETY * axis_fit_ratio)
            recommended_per_axis = cur_scale * per_axis_k
            msg = header + (
                f"  原因: オブジェクトサイズが解析空間サイズを超えています "
                f"(軸別 空間/物体 比 = {np.round(axis_fit_ratio,4).tolist()}, 1.0未満の軸が超過)。\n"
                f"  推奨オブジェクト倍率:\n"
                f"    - アスペクト比保持 scale = {np.round(recommended_uniform,6).tolist()}\n"
                f"    - 軸別に最小化    scale = {np.round(recommended_per_axis,6).tolist()}\n"
                f"    設定ファイルの \"scale\" をいずれかに書き換えてください"
                f"（配置も解析空間内へ translation を調整してください）。\n"
                "===========================================================================\n"
            )
        else:
            msg = header + (
                f"  はみ出し量 (下側/上側): {np.round(np.maximum(over_low,0),4).tolist()} / "
                f"{np.round(np.maximum(over_high,0),4).tolist()}\n"
                "  原因: サイズは解析空間に収まりますが、translation（配置）により空間外へはみ出しています。\n"
                "  → translation を解析空間の内側へ修正してください。\n"
                "===========================================================================\n"
            )

        if self.enforce_domain_fit:
            sys.exit(msg)
        else:
            print("[WARN]" + msg)

    def load_rigid_body(self, rigid_body):
        obj_id = rigid_body["objectId"]
        mesh = tm.load(rigid_body["geometryFile"])

        # --- scale（オブジェクト倍率）の妥当性チェック ---
        scale = np.array(rigid_body["scale"], dtype=np.float64)
        if not np.all(np.isfinite(scale)) or np.any(scale <= 0.0):
            sys.exit(
                f"\n[ERROR] RigidBody objectId={obj_id}: \"scale\" は各軸で正の有限値である必要があります "
                f"（指定値: {rigid_body['scale']}）。\n"
            )
        mesh.apply_scale(rigid_body["scale"])
        offset = np.array(rigid_body["translation"])

        # 回転処理（安全に行う）
        angle_deg = rigid_body.get("rotationAngle", 0)
        axis = np.array(rigid_body.get("rotationAxis", [0, 0, 0]), dtype=np.float64)
        angle_rad = angle_deg / 360 * 2 * np.pi

        # 有効な回転のみ適用（axis ≠ 0ベクトルかつ angle ≠ 0）
        if np.linalg.norm(axis) > 1e-6 and angle_deg != 0:
            rot_matrix = tm.transformations.rotation_matrix(
                angle_rad, axis, mesh.vertices.mean(axis=0)
            )
            mesh.apply_transform(rot_matrix)
        else:
            print(f"[INFO] Skipping rotation for RigidBody ID={obj_id} due to null axis or zero angle.")

        #angle = rigid_body["rotationAngle"] / 360 * 2 * 3.1415926
        #direction = rigid_body["rotationAxis"]
        #rot_matrix = tm.transformations.rotation_matrix(angle, direction, mesh.vertices.mean(axis=0))
        #mesh.apply_transform(rot_matrix)
        mesh.vertices += offset

        # メッシュポリゴンデータの数値誤差対策（正規化はしない・実寸は保持）
        self._clean_mesh(mesh, obj_id)

        # scale 適用後の実寸が解析空間に収まるか検証（大きすぎれば推奨倍率を出して終了）
        world_min = mesh.vertices.min(axis=0)
        world_max = mesh.vertices.max(axis=0)
        self._check_object_fits_domain(obj_id, scale, world_min, world_max)

        # Backup the original mesh for exporting obj
        mesh_backup = mesh.copy()
        rigid_body["mesh"] = mesh_backup
        rigid_body["restPosition"] = mesh_backup.vertices
        rigid_body["restCenterOfMass"] = mesh_backup.vertices.mean(axis=0)
        is_success = tm.repair.fill_holes(mesh)
            # print("Is the mesh successfully repaired? ", is_success)
        voxelized_mesh = mesh.voxelized(pitch=self.particle_diameter)
        voxelized_mesh = mesh.voxelized(pitch=self.particle_diameter).fill()
        # voxelized_mesh = mesh.voxelized(pitch=self.particle_diameter).hollow()
        # voxelized_mesh.show()
        voxelized_points_np = voxelized_mesh.points
        print(f"rigid body {obj_id} num: {voxelized_points_np.shape[0]}")
        if voxelized_points_np.shape[0] == 0:
            sys.exit(
                f"\n[ERROR] RigidBody objectId={obj_id}: ボクセル化で粒子が0個になりました。"
                f"オブジェクトが粒子径 {self.particle_diameter} に対して小さすぎます。"
                f"\"scale\" を大きくするか particleRadius を小さくしてください。\n"
            )

        ''' デバッグ用確認
        # 1. 基本情報出力
        print(f"[DEBUG] Loading Rigid Body ID: {rigid_body.get('objectId')}")
        print(f"[DEBUG] Geometry file: {rigid_body.get('geometryFile')}")
        print(f"[DEBUG] Scale: {rigid_body.get('scale')}")
        print(f"[DEBUG] Translation: {rigid_body.get('translation')}")
    
        # 2. メッシュ読み込みとスケーリング
        print(f"[DEBUG] mesh.vertices shape: {mesh.vertices.shape}")

        if "scale" in rigid_body:
            mesh.apply_scale(rigid_body["scale"])
        if "translation" in rigid_body:
            mesh.apply_translation(rigid_body["translation"])

        print(f"[DEBUG] mesh.bounds after transform: {mesh.bounds}")
        '''
        
        return voxelized_points_np


    def compute_cube_particle_num(self, start, end):
        num_dim = []
        for i in range(self.dim):
            num_dim.append(
                np.arange(start[i], end[i], self.particle_diameter))
        return reduce(lambda x, y: x * y,
                                   [len(n) for n in num_dim])

    def add_cube(self,
                 object_id,
                 lower_corner,
                 cube_size,
                 material,
                 is_dynamic,
                 color=(0,0,0),
                 density=None,
                 pressure=None,
                 velocity=None):

        num_dim = []
        for i in range(self.dim):
            num_dim.append(
                np.arange(lower_corner[i], lower_corner[i] + cube_size[i],
                          self.particle_diameter))
        num_new_particles = reduce(lambda x, y: x * y,
                                   [len(n) for n in num_dim])
        print('particle num ', num_new_particles)

        new_positions = np.array(np.meshgrid(*num_dim,
                                             sparse=False,
                                             indexing='ij'),
                                 dtype=np.float32)
        new_positions = new_positions.reshape(-1,
                                              reduce(lambda x, y: x * y, list(new_positions.shape[1:]))).transpose()
        print("new position shape ", new_positions.shape)
        if velocity is None:
            velocity_arr = np.full_like(new_positions, 0, dtype=np.float32)
        else:
            velocity_arr = np.array([velocity for _ in range(num_new_particles)], dtype=np.float32)

        material_arr = np.full_like(np.zeros(num_new_particles, dtype=np.int32), material)
        is_dynamic_arr = np.full_like(np.zeros(num_new_particles, dtype=np.int32), is_dynamic)
        color_arr = np.stack([np.full_like(np.zeros(num_new_particles, dtype=np.int32), c) for c in color], axis=1)
        density_arr = np.full_like(np.zeros(num_new_particles, dtype=np.float32), density if density is not None else 1000.)
        pressure_arr = np.full_like(np.zeros(num_new_particles, dtype=np.float32), pressure if pressure is not None else 0.)
        self.add_particles(object_id, num_new_particles, new_positions, velocity_arr, density_arr, pressure_arr, material_arr, is_dynamic_arr, color_arr)