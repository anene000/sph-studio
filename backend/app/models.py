"""Pydantic models mirroring the scene JSON schema (kept in sync with
``apps/web/lib/schema.ts``). Used to validate import/export payloads.

The models are intentionally permissive (extra keys allowed) so the schema can
evolve without breaking older scene files, while still validating the core fields.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

Vec3 = List[float]


class Configuration(BaseModel):
    """① Analysis space + solver / field-physics / simulation settings.

    Field-physics knobs actually consumed by the solver:
      - gravitation, density0            (sph_base)
      - stiffness, exponent              (WCSPH state equation)
      - viscosity                        (sph_base viscosity force)
      - surfaceTension                   (WCSPH/DFSPH non-pressure force)
      - timeStepSize, particleRadius, simulationMethod
    ``boundaryHandlingMethod`` is kept for template compatibility; the current
    solver uses a fixed collision-based boundary (see sph_base.enforce_boundary_3D).
    """

    model_config = {"extra": "allow"}

    domainStart: Vec3
    domainEnd: Vec3
    particleRadius: float = 0.01
    simulationMethod: int = 0  # 0=WCSPH, 4=DFSPH
    timeStepSize: float = 4e-4
    gravitation: Vec3 = Field(default_factory=lambda: [0.0, -9.81, 0.0])
    density0: float = 1000.0
    # WCSPH state-equation parameters (P = stiffness * ((rho/rho0)^exponent - 1)).
    stiffness: float = 50000.0
    exponent: float = 7.0
    # Field physics (previously hard-coded in the solver, now configurable).
    viscosity: float = 0.01
    surfaceTension: float = 0.01
    boundaryHandlingMethod: int = 0
    enforceDomainFit: bool = True
    numberOfStepsPerRenderUpdate: int = 1
    totalTime: Optional[float] = 5.0
    totalSteps: Optional[int] = None

    @model_validator(mode="after")
    def _check_domain(self):
        if len(self.domainStart) != len(self.domainEnd):
            raise ValueError("domainStart and domainEnd must have the same length")
        for a, b in zip(self.domainStart, self.domainEnd, strict=False):
            if b <= a:
                raise ValueError("domainEnd must be strictly greater than domainStart on every axis")
        return self


class RigidBody(BaseModel):
    model_config = {"extra": "allow"}

    objectId: int
    geometryFile: str
    translation: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: Vec3 = Field(default_factory=lambda: [1.0, 1.0, 1.0])
    rotationAxis: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotationAngle: float = 0.0
    velocity: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    density: float = 1000.0
    color: List[int] = Field(default_factory=lambda: [255, 255, 255])
    isDynamic: bool = False


class Block(BaseModel):
    model_config = {"extra": "allow"}

    objectId: int
    start: Vec3
    end: Vec3
    translation: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: Vec3 = Field(default_factory=lambda: [1.0, 1.0, 1.0])
    velocity: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    density: float = 1000.0
    color: List[int] = Field(default_factory=lambda: [50, 100, 200])
    isDynamic: bool = False


class ExportInterval(BaseModel):
    mode: Literal["steps", "time"] = "steps"
    value: float = 40


class ExportFluid(BaseModel):
    enabled: bool = True
    objectIds: Optional[List[int]] = None
    fields: List[str] = Field(default_factory=lambda: ["position", "velocity", "density", "pressure"])
    format: Literal["csv"] = "csv"


class ExportObject(BaseModel):
    objectId: int
    mode: Literal["particles", "meshVertices"] = "particles"
    fields: List[str] = Field(default_factory=lambda: ["position"])
    format: Literal["csv"] = "csv"


class ExportConfig(BaseModel):
    model_config = {"extra": "allow"}

    outputDir: Optional[str] = None
    interval: ExportInterval = Field(default_factory=ExportInterval)
    fluid: ExportFluid = Field(default_factory=ExportFluid)
    objects: List[ExportObject] = Field(default_factory=list)
    ply: bool = False
    obj: bool = False


class Scene(BaseModel):
    model_config = {"extra": "allow"}

    Configuration: Configuration
    RigidBodies: List[RigidBody] = Field(default_factory=list)
    FluidBlocks: List[Block] = Field(default_factory=list)
    RigidBlocks: List[Block] = Field(default_factory=list)
    Export: ExportConfig = Field(default_factory=ExportConfig)
