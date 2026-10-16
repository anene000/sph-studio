import numpy as np
import taichi as ti


@ti.data_oriented
class SPHBase:
    def __init__(self, particle_system):
        self.ps = particle_system
        self.g = ti.Vector([0.0, -9.81, 0.0])  # Gravity
        if self.ps.dim == 2:
            self.g = ti.Vector([0.0, -9.81])
        self.g = np.array(self.ps.cfg.get_cfg("gravitation"))

        # Kinematic viscosity of the fluid (field physics). Configurable; falls back
        # to the historical default when the scene omits the key.
        self.viscosity = 0.01  # viscosity
        _visc = self.ps.cfg.get_cfg("viscosity")
        if _visc is not None:
            self.viscosity = _visc

        # Boundary (wall) viscosity: momentum transfer from solid walls to the fluid.
        # Historically hard-coded to 0 (free-slip). Set > 0 so a moving/rotating wall
        # (e.g. a kinematic spinning shaft) can drag the fluid (no-slip drive).
        self.boundary_viscosity = 0.0
        _bvisc = self.ps.cfg.get_cfg("boundaryViscosity")
        if _bvisc is not None:
            self.boundary_viscosity = _bvisc

        self.density_0 = 1000.0  # reference density
        self.density_0 = self.ps.cfg.get_cfg("density0")

        self.dt = ti.field(float, shape=())
        self.dt[None] = 1e-4

        # Driving body force (acceleration, m/s^2) applied to fluid particles.
        # Used to maintain the flow in a periodic / fully-developed channel by
        # emulating a constant pressure gradient. Defaults to zero (no driving).
        drive = self.ps.cfg.get_cfg("drivingForce")
        if drive is None:
            drive = [0.0] * self.ps.dim
        assert len(drive) == self.ps.dim, \
            f"drivingForce must have length {self.ps.dim}, got {drive}"
        self.drive_force = np.array(drive, dtype=np.float64)

    @ti.func
    def cubic_kernel(self, r_norm, h):
        # `h` is the smoothing length (support radius) for this interaction. It is
        # passed per-call so that fluid blocks can use their own particle size
        # (multi-resolution SPH); with a uniform resolution h == ps.support_radius
        # for every call, reproducing the original single-resolution behavior.
        res = ti.cast(0.0, ti.f32)
        # value of cubic spline smoothing kernel
        k = 1.0
        if self.ps.dim == 1:
            k = 4 / 3
        elif self.ps.dim == 2:
            k = 40 / 7 / np.pi
        elif self.ps.dim == 3:
            k = 8 / np.pi
        k /= h ** self.ps.dim
        q = r_norm / h
        if q <= 1.0:
            if q <= 0.5:
                q2 = q * q
                q3 = q2 * q
                res = k * (6.0 * q3 - 6.0 * q2 + 1)
            else:
                res = k * 2 * ti.pow(1 - q, 3.0)
        return res

    @ti.func
    def cubic_kernel_derivative(self, r, h):
        # derivative of cubic spline smoothing kernel (see cubic_kernel for `h`)
        k = 1.0
        if self.ps.dim == 1:
            k = 4 / 3
        elif self.ps.dim == 2:
            k = 40 / 7 / np.pi
        elif self.ps.dim == 3:
            k = 8 / np.pi
        k = 6. * k / h ** self.ps.dim
        r_norm = r.norm()
        q = r_norm / h
        res = ti.Vector([0.0 for _ in range(self.ps.dim)])
        if r_norm > 1e-5 and q <= 1.0:
            grad_q = r / (r_norm * h)
            if q <= 0.5:
                res = k * q * (3.0 * q - 2.0) * grad_q
            else:
                factor = 1.0 - q
                res = k * (-factor * factor) * grad_q
        return res

    @ti.func
    def h_ij(self, p_i, p_j):
        # Symmetric smoothing length for a pair (mean of the two support radii).
        return 0.5 * (self.ps.support_r[p_i] + self.ps.support_r[p_j])

    @ti.func
    def transport_accel(self, p_i):
        # Summed transport-force acceleration for a fluid particle inside any pipe
        # pump zone (axis-aligned box). Zero when outside all zones / no zones.
        acc = ti.Vector([0.0 for _ in range(self.ps.dim)])
        for z in ti.static(range(self.ps.n_transport)):
            inside = True
            for d in ti.static(range(self.ps.dim)):
                if self.ps.x[p_i][d] < self.ps.transport_min[z][d] or \
                   self.ps.x[p_i][d] > self.ps.transport_max[z][d]:
                    inside = False
            if inside:
                acc += self.ps.transport_force[z]
        return acc

    @ti.func
    def viscosity_force(self, p_i, p_j, r):
        # Compute the viscosity force contribution
        h = self.h_ij(p_i, p_j)
        v_xy = (self.ps.v[p_i] -
                self.ps.v[p_j]).dot(r)
        res = 2 * (self.ps.dim + 2) * self.viscosity * (self.ps.m[p_j] / (self.ps.density[p_j])) * v_xy / (
            r.norm()**2 + 0.01 * h**2) * self.cubic_kernel_derivative(
                r, h)
        return res

    def initialize(self):
        self.ps.initialize_particle_system()
        for r_obj_id in self.ps.object_id_rigid_body:
            self.compute_rigid_rest_cm(r_obj_id)
        self.compute_static_boundary_volume()
        self.compute_moving_boundary_volume()

    @ti.kernel
    def compute_rigid_rest_cm(self, object_id: int):
        self.ps.rigid_rest_cm[object_id] = self.compute_com(object_id)

    @ti.kernel
    def compute_static_boundary_volume(self):
        pn = self.ps.particle_num[None]
        for p_i in range(pn):
        #for p_i in ti.grouped(self.ps.x):
            if not self.ps.is_static_rigid_body(p_i):
                continue
            delta = self.cubic_kernel(0.0, self.ps.support_r[p_i])
            self.ps.for_all_neighbors(p_i, self.compute_boundary_volume_task, delta)
            self.ps.m_V[p_i] = 1.0 / delta * 3.0  # TODO: the 3.0 here is a coefficient for missing particles by trail and error... need to figure out how to determine it sophisticatedly

    @ti.func
    def compute_boundary_volume_task(self, p_i, p_j, r: ti.template(), delta: ti.template()):
        if self.ps.material[p_j] == self.ps.material_solid:
            delta += self.cubic_kernel(r.norm(), self.ps.support_r[p_i])


    @ti.kernel
    def compute_moving_boundary_volume(self):
        pn = self.ps.particle_num[None]
        for p_i in range(pn):
        #for p_i in ti.grouped(self.ps.x):
            if not self.ps.is_dynamic_rigid_body(p_i):
                continue
            delta = self.cubic_kernel(0.0, self.ps.support_r[p_i])
            self.ps.for_all_neighbors(p_i, self.compute_boundary_volume_task, delta)
            self.ps.m_V[p_i] = 1.0 / delta * 3.0  # TODO: the 3.0 here is a coefficient for missing particles by trail and error... need to figure out how to determine it sophisticatedly

    def substep(self):
        pass

    @ti.func
    def simulate_collisions(self, p_i, vec):
        # Collision factor, assume roughly (1-c_f)*velocity loss after collision
        c_f = 0.5
        self.ps.v[p_i] -= (
            1.0 + c_f) * self.ps.v[p_i].dot(vec) * vec

    @ti.func
    def wrap_periodic_axis(self, p_i, d: ti.template()):
        # Recirculate a particle that crossed a periodic boundary back to the
        # opposite side of the domain (fixed particle count, no emission/removal).
        size = self.ps.domain_end_ti[None][d] - self.ps.domain_start_ti[None][d]
        if self.ps.x[p_i][d] >= self.ps.domain_end_ti[None][d]:
            self.ps.x[p_i][d] -= size
        if self.ps.x[p_i][d] < self.ps.domain_start_ti[None][d]:
            self.ps.x[p_i][d] += size

    @ti.kernel
    def enforce_boundary_2D(self, particle_type:int):
        pn = self.ps.particle_num[None]
        for p_i in range(pn):
        #for p_i in ti.grouped(self.ps.x):
            if self.ps.material[p_i] == particle_type and self.ps.is_dynamic[p_i]:
                pos = self.ps.x[p_i]
                collision_normal = ti.Vector([0.0, 0.0])
                for d in ti.static(range(2)):
                    if self.ps.periodic_ti[None][d] == 1:
                        self.wrap_periodic_axis(p_i, d)
                    else:
                        if pos[d] > self.ps.domain_size[d] - self.ps.padding:
                            collision_normal[d] += 1.0
                            self.ps.x[p_i][d] = self.ps.domain_size[d] - self.ps.padding
                        if pos[d] <= self.ps.padding:
                            collision_normal[d] += -1.0
                            self.ps.x[p_i][d] = self.ps.padding
                collision_normal_length = collision_normal.norm()
                if collision_normal_length > 1e-6:
                    self.simulate_collisions(
                            p_i, collision_normal / collision_normal_length)

    @ti.kernel
    def enforce_boundary_3D(self, particle_type:int):
        pn = self.ps.particle_num[None]
        for p_i in range(pn):
        #for p_i in ti.grouped(self.ps.x):
            if self.ps.material[p_i] == particle_type and self.ps.is_dynamic[p_i]:
                pos = self.ps.x[p_i]
                collision_normal = ti.Vector([0.0, 0.0, 0.0])
                for d in ti.static(range(3)):
                    if self.ps.periodic_ti[None][d] == 1:
                        self.wrap_periodic_axis(p_i, d)
                    else:
                        if pos[d] > self.ps.domain_size[d] - self.ps.padding:
                            collision_normal[d] += 1.0
                            self.ps.x[p_i][d] = self.ps.domain_size[d] - self.ps.padding
                        if pos[d] <= self.ps.padding:
                            collision_normal[d] += -1.0
                            self.ps.x[p_i][d] = self.ps.padding

                collision_normal_length = collision_normal.norm()
                if collision_normal_length > 1e-6:
                    self.simulate_collisions(
                            p_i, collision_normal / collision_normal_length)


    @ti.func
    def compute_com(self, object_id):
        sum_m = 0.0
        cm = ti.Vector([0.0, 0.0, 0.0])
        for p_i in range(self.ps.particle_num[None]):
            if self.ps.is_dynamic_rigid_body(p_i) and self.ps.object_id[p_i] == object_id:
                mass = self.ps.m_V0 * self.ps.density[p_i]
                cm += mass * self.ps.x[p_i]
                sum_m += mass
        cm /= sum_m
        return cm
    

    @ti.kernel
    def compute_com_kernel(self, object_id: int)->ti.types.vector(3, float):
        return self.compute_com(object_id)


    @ti.kernel
    def solve_constraints(self, object_id: int) -> ti.types.matrix(3, 3, float):
        # compute center of mass
        cm = self.compute_com(object_id)
        # A
        A = ti.Matrix([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        for p_i in range(self.ps.particle_num[None]):
            if self.ps.is_dynamic_rigid_body(p_i) and self.ps.object_id[p_i] == object_id:
                q = self.ps.x_0[p_i] - self.ps.rigid_rest_cm[object_id]
                p = self.ps.x[p_i] - cm
                A += self.ps.m_V0 * self.ps.density[p_i] * p.outer_product(q)

        R, S = ti.polar_decompose(A)
        
        if all(abs(R) < 1e-6):
            R = ti.Matrix.identity(ti.f32, 3)
        
        for p_i in range(self.ps.particle_num[None]):
            if self.ps.is_dynamic_rigid_body(p_i) and self.ps.object_id[p_i] == object_id:
                goal = cm + R @ (self.ps.x_0[p_i] - self.ps.rigid_rest_cm[object_id])
                corr = (goal - self.ps.x[p_i]) * 1.0
                self.ps.x[p_i] += corr
        return R
        

    # @ti.kernel
    # def compute_rigid_collision(self):
    #     # FIXME: This is a workaround, rigid collision failure in some cases is expected
    #     for p_i in range(self.ps.particle_num[None]):
    #         if not self.ps.is_dynamic_rigid_body(p_i):
    #             continue
    #         cnt = 0
    #         x_delta = ti.Vector([0.0 for i in range(self.ps.dim)])
    #         for j in range(self.ps.solid_neighbors_num[p_i]):
    #             p_j = self.ps.solid_neighbors[p_i, j]

    #             if self.ps.is_static_rigid_body(p_i):
    #                 cnt += 1
    #                 x_j = self.ps.x[p_j]
    #                 r = self.ps.x[p_i] - x_j
    #                 if r.norm() < self.ps.particle_diameter:
    #                     x_delta += (r.norm() - self.ps.particle_diameter) * r.normalized()
    #         if cnt > 0:
    #             self.ps.x[p_i] += 2.0 * x_delta # / cnt
                        


    def solve_rigid_body(self):
        for i in range(1):
            for r_obj_id in self.ps.object_id_rigid_body:
                if self.ps.object_collection[r_obj_id]["isDynamic"]:
                    R = self.solve_constraints(r_obj_id)

                    if self.ps.cfg.get_cfg("exportObj"):
                        # For output obj only: update the mesh
                        cm = self.compute_com_kernel(r_obj_id)
                        ret = R.to_numpy() @ (self.ps.object_collection[r_obj_id]["restPosition"] - self.ps.object_collection[r_obj_id]["restCenterOfMass"]).T
                        self.ps.object_collection[r_obj_id]["mesh"].vertices = cm.to_numpy() + ret.T

                    # self.compute_rigid_collision()
                    self.enforce_boundary_3D(self.ps.material_solid)


    @ti.kernel
    def apply_inlet_velocity(self):
        # Impose the target inlet velocity (optionally a parabolic profile) on fluid
        # particles inside the inlet zone. Velocity is relaxed toward the target so
        # the inflow is a dynamic condition, not a hard fixed value. Applied every
        # step; only affects particles that have actually reached the inlet zone, so
        # an initially under-filled domain fills/follows smoothly.
        ax = ti.static(self.ps.inlet_axis)
        pax = ti.static(self.ps.profile_axis)
        pn = self.ps.particle_num[None]
        for p_i in range(pn):
            if self.ps.material[p_i] == self.ps.material_fluid and self.ps.is_dynamic[p_i]:
                pos = self.ps.x[p_i]
                lo = self.ps.domain_start_ti[None][ax]
                hi = self.ps.domain_end_ti[None][ax]
                in_zone = False
                if ti.static(self.ps.inlet_side_low):
                    in_zone = pos[ax] <= lo + self.ps.inlet_thickness
                else:
                    in_zone = pos[ax] >= hi - self.ps.inlet_thickness
                if in_zone:
                    factor = 1.0
                    if ti.static(self.ps.inlet_parabolic):
                        plo = self.ps.domain_start_ti[None][pax]
                        phi = self.ps.domain_end_ti[None][pax]
                        center = 0.5 * (plo + phi)
                        half = 0.5 * (phi - plo)
                        t = (pos[pax] - center) / half
                        factor = ti.max(0.0, 1.0 - t * t)
                    target = self.ps.inlet_velocity_ti[None] * factor
                    self.ps.v[p_i] += self.ps.inlet_relaxation * (target - self.ps.v[p_i])

    @ti.kernel
    def advance_spin_object(self, object_id: int, omega: float,
                            ax: float, ay: float, az: float,
                            cx: float, cy: float, cz: float):
        # Kinematic (prescribed) axis rotation of a solid object: rotate its particles
        # about the axis (through center) by omega*dt and set their velocity to the
        # rigid-body velocity w x r. Position is otherwise fixed and the object is not
        # affected by the fluid (prescribed motion, not PBD). The fluid feels the wall
        # velocity through the boundary viscosity term (no-slip drive).
        k = ti.Vector([ax, ay, az])
        center = ti.Vector([cx, cy, cz])
        dtheta = omega * self.dt[None]
        c = ti.cos(dtheta)
        s = ti.sin(dtheta)
        pn = self.ps.particle_num[None]
        for p_i in range(pn):
            if self.ps.material[p_i] == self.ps.material_solid and self.ps.object_id[p_i] == object_id:
                r = self.ps.x[p_i] - center
                # Rodrigues rotation of r about unit axis k by dtheta
                r_rot = r * c + k.cross(r) * s + k * (k.dot(r)) * (1.0 - c)
                self.ps.x[p_i] = center + r_rot
                # Rigid-body velocity of the wall particle: w x r (w = omega * k)
                self.ps.v[p_i] = (omega * k).cross(r_rot)

    def advance_spins(self):
        # Apply the prescribed rotation to every configured spin object.
        for so in self.ps.spin_objects:
            ax, ay, az = so["axis"]
            cx, cy, cz = so["center"]
            self.advance_spin_object(int(so["objectId"]), float(so["omega"]),
                                     float(ax), float(ay), float(az),
                                     float(cx), float(cy), float(cz))

    def step(self):
        if self.ps.spin_objects:
            self.advance_spins()
        self.ps.initialize_particle_system()
        self.compute_moving_boundary_volume()
        self.substep()
        self.solve_rigid_body()
        if self.ps.dim == 2:
            self.enforce_boundary_2D(self.ps.material_fluid)
        elif self.ps.dim == 3:
            self.enforce_boundary_3D(self.ps.material_fluid)
        if self.ps.inlet_control:
            self.apply_inlet_velocity()
