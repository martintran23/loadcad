# LoadCAD Context

Persistent source of truth for contributors and future Cursor Agent sessions.

| | |
| --- | --- |
| Last updated | 2026-11-24 |
| Current phase | 2 — materials, metrics, and mesh refinement, recorded. Pre-MVP |
| Implementation | Headless pipeline under `backend/`. No API, database, or UI |
| Simulations run by this project | Phase 1 solves and the Phase 2 refinement studies in section 9. Not a validated design method |

Read this file before changing architecture, dependencies, geometry, meshing, or solver behavior. Read [README.md](README.md) for the product summary. If a coding session discovers that this file is wrong, update it in the same session with the evidence, and label anything still unmeasured as an open question.

Measured results are in section 9 and in the open-question answers below. Anything not tied to those runs is still a plan.

## 1. Project Identity

### Name

LoadCAD

### Vision

Make mechanical design more accessible by generating, simulating, and iteratively revising a part from its physical requirements, with the modeling assumptions left visible.

### Mission

Build a verifiable path from a constrained design request to a parametric solid, a finite-element result, and exportable CAD files. Start with one part family and one linear-static load case. Expand only after numerical checks exist.

### Product philosophy

- Geometry, loads, and materials are explicit engineering inputs. A language model may help develop the software. It does not author the solid or the stress answer.
- A narrow, testable bracket is more valuable than a general shape generator.
- Solver completion is a numerical event. Engineering adequacy is a separate claim and requires stated assumptions, mesh evidence, and, eventually, physical checks.
- The software suggests design candidates. It does not certify them.
- Reproducible files beat a polished viewer. The viewer comes after the files are trustworthy.
- Prefer fewer services. Add infrastructure when a local pipeline has outgrown it.

### Core value proposition

**Describe what a part needs to withstand. LoadCAD designs and simulates it.**

The planned product combines parametric CAD, automated meshing, linear finite-element analysis, bounded dimensional changes, lightweight manufacturing checks, interactive 3D review, and CAD export.

## 2. Current Development State

### Current phase

Phase 0 was completed on 2026-11-22. Phase 1 was approved on 2026-11-23. Phase 2 was approved on 2026-11-24. Both are recorded in section 9. Phase 3 is not approved.

### Existing files

Phase 0 added `README.md` and `CONTEXT.md`. Phase 1 added `backend/` (package, tests, and `requirements.lock`), `.gitignore`, and a gitignored CalculiX directory under `tools/calculix/`. Phase 2 added the material cards, the metric and safety-factor code, and the study tables in `backend/studies/`. Job output is under gitignored `artifacts/`. There is still no `LICENSE`, frontend, API package, or search package.

`dev` contains the Phase 1 commits `b2414b6` and `28b272a`. Phase 2 is in the working tree and is not committed.

### Environment observed on 2026-11-22

Observed locally. These are machine facts, not project requirements.

| Check | Result |
| --- | --- |
| Operating system | Windows |
| Repository path | `C:\Users\Martin Tran\Documents\loadcad` |
| Python | 3.12.6, from the per-user Python install |
| Git | 2.45.1 |
| `ccx` on `PATH` | Not found |
| `gmsh` on `PATH` | Not found |
| `conda` on `PATH` | Not found |
| `build123d` import | Not available |
| `gmsh` import | Not available |
| `meshio` import | Not available |
| `numpy`, `scipy`, `fastapi`, `pydantic` imports | Available in the system interpreter |

The system packages are incidental. Phase 1 must use a project virtual environment. Do not install LoadCAD dependencies into the global interpreter.

The repository path contains a space. Q9 was checked on 2026-11-23. A one-tet `ccx_static` solve and a Gmsh box write both succeeded under `artifacts/phase1/path-with-space` and under `C:\Temp\loadcad-phase1\path-nospace`. The space did not break those two operations. Job output for the beam and bracket stayed under the repository path.

### Implemented functionality

- Product scope, pipeline, unit system, and phase gates are written down.
- A project virtual environment and `backend/requirements.lock`.
- Filleted L-bracket and rectangular-cantilever constructors, STEP and STL export, Gmsh import, geometric face match, `C3D10` decks, `ccx` execution, FRD parsing, and von Mises post-processing.
- One recorded cantilever solve and one recorded bracket solve from Phase 1. Those two result files keep `decision_metric` and `estimated_safety_factor` null.
- Cited cards for 6061-T6, Prusament PLA, and Prusament PETG. Only the aluminum card can be solved.
- Beam and bracket refinement studies at 5, 2.5, and 1.25 mm, stored in `backend/studies/`. The bracket decision metric is `max_nodal_von_mises`. Its safety-factor record has `mesh_converged` false.
- Rejection of a zero fillet before meshing, and classification of an unrestrained solid that still exits 0.
- Automated tests for units, geometry, mesh order, face match, solver I/O, materials, the failure cases, the stored study, and the two Phase 1 solves. On 2026-11-24 the project environment passed 32 tests in 11.21 seconds. The earlier 22-test run remains the Phase 1 record.

### Unimplemented functionality

- A mesh-converged stress result. The Phase 2 factor is stored with `mesh_converged` false
- Parameter search
- HTTP API, database, web UI, authentication, and deployment

### Known blockers

1. The project license is unset, and GPL obligations from Gmsh and CalculiX constrain a future proprietary distribution. Q10 is still open.
2. No stress convergence band is adopted. The bracket nodal peak rose on the last refinement. See section 9.
3. Prusament PLA and PETG have no cited Poisson ratio, so those cards cannot be solved.
4. The bracket reaction is still short of the 100 N load after the quadratic-area change. The shortfall is smaller than in Phase 1 and is not closed.
5. No fillet radius has a stored stress result that flattens under refinement. Q11 has no minimum.
6. CalculiX, build123d, Gmsh, face match, and `C3D10` order were checked in Phase 1. Those Phase 0 blockers are not open.

## 3. Technical Architecture

### Major components

| Component | Role in the MVP | When it appears |
| --- | --- | --- |
| Geometry module | Build one solid L-bracket from validated numbers. Export STEP and STL. Write face fingerprints | Phase 1 |
| Mesh module | Import the solid, rematch faces, set physical groups, generate and grade the mesh | Phase 1 |
| Deck writer | Write a CalculiX `.inp` from mesh tables and an internal material card | Phase 1, hardened in Phase 2 |
| Solver runner | Execute `ccx` in a job directory with a timeout and captured logs | Phase 1 |
| Post-processor | Read displacements and stress components. Compute von Mises stress and a labeled safety-factor estimate | Phase 1 skeleton, Phase 2 definition |
| Material library | Versioned cards with citations and allowable-stress basis | Phase 2 |
| Search module | Deterministic changes of thickness and fillet radius | Phase 3 |
| Job runner | Status transitions, artifact index, failure mapping | Phase 1 files, Phase 4 service |
| API | HTTP boundary that accepts a design request and returns job status and files | Phase 4 |
| Web viewer | Geometry, stress colors, assumptions, downloads | Phase 5 |

### Data flow

```text
DesignRequest
    -> validation
    -> GeometryParameters checked against manufacturing heuristics
    -> build123d solid
    -> face fingerprints + STEP (mm) + STL (mm, unitless file)
    -> Gmsh OCC import
    -> bounding-box check against the CAD model
    -> unique face match
    -> physical groups
    -> second-order tetrahedral mesh
    -> CalculiX deck written by LoadCAD
    -> ccx subprocess
    -> .frd / .dat / log
    -> nodal displacement and stress components
    -> von Mises metric + assumptions
    -> pass/fail against target safety factor and geometry limits
    -> optional bounded regeneration
    -> export bundle and, later, a browser view
```

Modules in Phases 1–3 communicate by Python function calls and by files in the job directory. They must not communicate by editing a global mutable model in place. A stage can be rerun from its input files.

The API, once it exists, may only pass a validated `DesignRequest` into the same job runner. It must not accept a solver deck, a Python script, or a mesh written by the client.

### Module responsibilities and boundaries

**Validation** owns syntactic and physical feasibility checks. It does not build shapes.

**Geometry** owns the solid and the semantic face fingerprints. It does not know CalculiX exists.

**Meshing** owns element size, physical groups, and mesh-quality gates. It does not choose a safety factor.

**Deck writer** owns keyword cards, set names, and element connectivity. Its only inputs are mesh tables, matched set names, and a material card already parsed by LoadCAD.

**Solver runner** owns the process boundary, timeout, and logs. It does not interpret stress.

**Post-processor** owns von Mises math, the selected stress metric, and the safety-factor record. It does not regenerate geometry.

**Search** may change only fields marked as free variables. It calls the pipeline. It does not write solver cards itself.

**API and UI** display stored records. They do not recompute stress in the browser for the reported safety factor. The browser may color an already computed nodal field.

### Planned repository structure

Phase 1 created `backend/pyproject.toml`, `backend/requirements.lock`, `backend/src/loadcad/`, and flat test modules under `backend/tests/`. It did not create `materials/`, `optimization/`, `api/`, or `frontend/`. The test files are not split into the subfolders drawn below.

```text
loadcad/
  README.md
  CONTEXT.md
  backend/
    pyproject.toml
    src/loadcad/
      geometry/          # bracket construction and face fingerprints
      meshing/           # Gmsh import, match, mesh, quality gates
      solver/            # deck writer, ccx runner, output readers
      postprocess/       # von Mises, metrics, safety-factor record
      materials/         # versioned cards and citations
      optimization/      # Phase 3 search
      jobs/              # job directory, status, provenance
      api/               # Phase 4 only
    tests/
      analytical/        # beam formulas and comparisons
      geometry/
      meshing/
      solver/
  frontend/              # Phase 5 only
  artifacts/             # gitignored job output
```

Phase 1 should add only `geometry`, `meshing`, `solver`, `postprocess`, `jobs`, and `tests`. Leaving empty API and frontend trees in place encourages work outside the authorized phase.

### Job directory

One directory per solve. This is the system of record through Phase 3.

```text
artifacts/<job_id>/
  request.json
  status.json
  provenance.json
  logs/geometry.log
  logs/gmsh.log
  logs/ccx.log
  geometry/bracket.step
  geometry/bracket.stl
  geometry/face_map.json
  mesh/bracket.msh
  mesh/metadata.json
  solver/job.inp
  solver/job.frd
  solver/job.dat
  solver/job.sta
  results/results.json
```

A search adds `iterations/<n>/` with the same geometry, mesh, solver, and results layout, plus the parameter vector for that iteration.

`job_id` should be unique and not derived from unsanitized user text. A content hash of the canonical request, tool versions, and material-card version may be used later as a cache key. A cache hit is invalid if any of those versions differ. Phase 1 does not need a cache.

### Job lifecycle

```text
created
  -> validating
  -> building_geometry
  -> meshing
  -> solving
  -> postprocessing
  -> completed
```

Any stage may instead go to `failed`. A search job may enter `iterating` between post-processing and completion. Cancellation, once an API exists, stops before the next stage and does not delete the logs already written.

`completed` means every requested stage finished and the results file was written. It does not mean the design met its safety-factor target. Target satisfaction is a field on the result.

A failed mesh, unmatched face, nonzero solver status, missing output, timeout, or singular model is `failed`. No safety factor is written for a failed solve. Partial numbers may exist in a log, and they stay in the log.

Suggested failure codes, to be adjusted when real errors appear:

| Code | Meaning |
| --- | --- |
| `request_invalid` | Schema or range check failed |
| `geometry_failed` | Kernel boolean or export failed |
| `face_match_failed` | A semantic face was missing or ambiguous |
| `mesh_quality_failed` | Quality gate or element-count guard failed |
| `solver_failed` | `ccx` returned an error, or the output was unusable |
| `solver_timeout` | The process exceeded the job limit |
| `result_unreadable` | Output files existed but could not be parsed |
| `assumption_exceeded` | Not a failure. The elastic estimate passed the allowable stress. The job can still complete |

### Artifact storage

- Keep large mesh and result files on disk.
- Write JSON beside them for anything a later phase must query.
- Store hashes of `bracket.step`, `job.inp`, and the results file in `provenance.json`.
- SQLite, introduced in Phase 4, stores job id, status, request summary, timestamps, and artifact paths. It does not store mesh blobs.
- MongoDB is not used. See ADR-005.

### Provenance

Every solve writes:

- LoadCAD source revision, once the code is in Git
- Python version
- build123d version and the Open CASCADE binding version it reports
- Gmsh version
- `ccx` version banner and the absolute path of the binary
- Thread setting, if one was fixed
- Material card id and version
- Canonical request
- Mesh options actually set
- Hashes of the STEP file and the input deck
- Start and finish timestamps, and solver wall time
- Platform

A result without provenance is not reportable.

### Safe execution

User input is data: numbers, booleans, and a closed set of enumerations. It is never code.

- Do not pass user strings into `eval`, `exec`, a shell command line, a Gmsh `.geo` string, or a CalculiX keyword.
- Set names written into the deck come from a fixed allow-list such as `FIXED_MOUNT`, `LOAD_FACE`, and `EALL`.
- The solver binary path is developer configuration, not a request field.
- Start `ccx` with an argument array, `shell=False`, a job working directory, a timeout, and a restricted environment.
- Cap runtime, output size, and element count before calling the solver.
- Generate the solid only from the bracket constructor. Do not import an arbitrary STEP file from a user in the MVP.
- Do not execute Python, journal files, or solver `*INCLUDE` paths supplied by a request.

## 4. MVP Requirements

The product MVP is the L-bracket flow through export and review. Phase 1 is only the headless proof that makes the later product possible. Exit criteria for each phase are in section 9.

### Functional requirements

1. Accept one L-bracket design request and reject malformed or non-finite input.
2. Generate a single solid with a horizontal leg, a vertical leg, one shared wall thickness, an inside fillet, and zero or more through-holes from the supported hole schema.
3. Export a millimetre STEP file and a millimetre STL file. The STL has no unit field, so the job metadata must state millimetres.
4. Build a volume mesh of 10-node tetrahedra, a node set for the mounting face, and an element-face set for the loaded face.
5. Assign one isotropic linear-elastic material from a versioned card.
6. Fix all three translations on the mounting-face node set.
7. Apply one static resultant force normal to the top of the horizontal leg.
8. Run CalculiX linear static analysis.
9. Extract displacement and Cauchy stress, then compute von Mises stress in post-processing.
10. Record an estimated safety factor using the metric defined in Phase 2, together with the assumptions.
11. Vary thickness and inside fillet radius across a bounded deterministic search, retaining every iteration.
12. Show geometry and stress coloring, and allow download of the design artifacts.

Items 11 and 12 are product-MVP requirements. They are not Phase 1 requirements.

### Nonfunctional requirements

- A job is reproducible from its directory and the recorded tool versions.
- Units stay in the millimetre–newton–second–megapascal system from request through deck.
- Face matching fails closed when it is ambiguous.
- Solver failure is visible and does not produce a safety factor.
- Dependency set stays small enough to install on one Windows workstation without a database server or a queue broker.
- Reports and UI copy must be able to show the disclaimer in section 5 without editing historical result files.
- Computation that affects a reported number is deterministic given the same versions and inputs. No random seed is required in the planned path.

### Explicit non-goals

The MVP does not include:

- Part families other than the L-bracket
- Topology optimization or free-form generative shapes
- Assemblies, fasteners as solids, welds, or multi-body contact
- Bolt preload, friction, or bearing-pressure checks
- More than one load case per solve
- Gravity, dynamics, modal analysis, buckling, fatigue, or thermal analysis
- Geometric or material nonlinearity
- Orthotropic or printed-infill material models
- User-uploaded CAD or user-written solver cards
- A claim of certification, code compliance, or experimental verification
- Cloud solving, accounts, billing, or multi-user collaboration
- MongoDB, Celery, Redis, or a hosted queue
- LLM-generated geometry or LLM-interpreted stress

CNC tool access, GD&T, tolerance stack-up, and slicer toolpaths are also out of scope. Manufacturing output in the MVP is a heuristic check plus STEP and STL files.

### Product MVP acceptance criteria

All of the following must be true before the product is described as an MVP. None are true today.

1. A documented cantilever-beam benchmark compares LoadCAD displacement with beam theory and records the mesh used.
2. A mesh-refinement study exists for that beam and for one bracket.
3. A valid bracket request produces STEP and STL files that a conventional CAD tool and a slicer can open.
4. The same request produces a completed CalculiX run whose parsed displacement and stress can be traced to stored `.frd` or `.dat` files.
5. The safety-factor record names the allowable stress, its basis, the von Mises metric, the fillet radius, the restraint model, and the mesh size.
6. A request with a zero fillet, an ambiguous face match, or a crashed solver finishes as a failed or rejected job and stores no safety factor.
7. At least one dimension can be changed and both solves remain stored.
8. The interface shows the geometry, a stress coloring of a precomputed field, the assumptions, and the downloads.
9. The interface does not describe the part as certified, safe, or experimentally verified.
10. A second person can rerun `ccx` from a saved job directory using the stored deck.

## 5. Engineering Assumptions

Assumptions in this section are design choices. They are not measured behavior. Phase 1 and Phase 2 either confirm them or replace them in this file.

### Unit system

LoadCAD uses one consistent unit system. CalculiX does not read units. The deck will be wrong if the geometry is in millimetres and the modulus is in pascals.

| Quantity | Unit | Example of scale |
| --- | --- | --- |
| Length | millimetre (mm) | Bracket dimensions |
| Force | newton (N) | Applied resultant |
| Time | second (s) | Only needed if mass is used |
| Stress and modulus | megapascal (MPa = N/mm²) | Steel is on the order of 2×10⁵ MPa, not 2×10¹¹ |
| Density, when stored | tonne per mm³ | 2700 kg/m³ = 2.7×10⁻⁹ tonne/mm³ |

This is the millimetre–newton–second system: 1 N = 1 tonne·mm/s². Storing a kilogram-per-cubic-metre density beside millimetre geometry is a unit bug.

The first verified load case applies no gravity and no inertia, so density does not affect that solve. Density is still stored in the converted unit so a later self-weight case does not inherit a silent factor of 10¹².

STEP export must set millimetres explicitly. After Gmsh imports the file, the mesh bounding box must match the CAD bounding box within a tolerance before any solve. Community Gmsh examples sometimes set `Geometry.OCCTargetUnit` to metres. LoadCAD must not do that while material cards are in MPa. The exact Gmsh option name has to be confirmed in the installed version.

STL is unitless. Metadata and any later UI must say millimetres.

Proposed sanity limits for the first bracket product, adjustable after timing data exists:

| Parameter | Proposed limit | Status |
| --- | --- | --- |
| Length, height, and width | 10 mm to 200 mm | Hypothesis, to keep early meshes small |
| Thickness | 2 mm to 20 mm, and less than both leg lengths | Hypothesis |
| Force magnitude | Greater than 0 and at most 10⁶ N | Product guard against non-physical input, not a structural cap |
| Modulus on a card | 100 MPa to 500 000 MPa | Reject cards outside this range until a new class is added |

The analytical beam used in tests may use its own dimensions. It is not subject to the product envelope.

### Coordinate conventions

Right-handed Cartesian coordinates, millimetres, global axes fixed to the bracket.

```text
Z (height)
^
|  #### vertical leg
|  #
|  #
|  ######## horizontal leg
+----------------------------> X (length)
/
Y (width), out of the page
```

- Origin: the outer corner where the outer vertical face, the outer bottom face, and the `Y = 0` side face meet.
- `+X`: along the horizontal leg.
- `+Y`: across the width.
- `+Z`: up the vertical leg.
- Vertical leg before holes and fillet: `x` from 0 to thickness, `y` from 0 to width, `z` from 0 to height.
- Horizontal leg before holes and fillet: `x` from 0 to length, `y` from 0 to width, `z` from 0 to thickness.
- The solid is the union of those legs, then the inside fillet, then the holes.
- Mounting face: the outer vertical planar face on `x = 0`, outward normal `−X`.
- First load face: the top of the horizontal leg, outward normal `+Z`, excluding the region occupied by the vertical leg and the fillet. The fingerprint is taken on the final solid, not on the pre-union rectangle.
- Vertical-leg holes are through-holes with axis parallel to X.
- Horizontal-leg holes are through-holes with axis parallel to Z.

Both legs share one thickness in the MVP. Independent leg thicknesses are a possible later parameter, not a hidden second interpretation of `thickness`.

### Supported materials

No material card is approved for implementation during Phase 0. Phase 2 adds cards. A card is data, with a citation, not a constant buried in solver code.

Candidate set:

| Card | Intended use | Modeling stance |
| --- | --- | --- |
| Aluminum 6061-T6 | Wrought isotropic metal baseline | Linear elastic. Allowable stress is tensile yield unless a cited card says otherwise |
| PLA | Printed bracket, isotropic approximation | Allowable stress must be an explicit card field. Do not invent a single yield value |
| PETG | Printed bracket, isotropic approximation | Same rule as PLA |

Commonly published nominal figures for 6061-T6, including a modulus near 68.9 GPa, Poisson's ratio near 0.33, density near 2.70 g/cm³, and a tensile yield near 276 MPa for many product forms, are planning context only. They must not be copied into a card until a specific ASM, MMPDS, or supplier source is read and cited. Phase 0 did not retrieve that source.

Printed PLA and PETG depend on grade, orientation, layer height, temperature, and infill. The MVP model is a homogeneous isotropic solid equal to the CAD volume. It does not model beads, infill percentage, or layer planes. A printed-part card therefore needs an `allowable_basis` of `specified_allowable`, a cited source, and text stating that the print is not the simulated solid.

Poisson's ratio must be greater than −1 and less than 0.5. A value of 0.5 is incompressible and is rejected for this solver path.

### FEA assumptions

The first analysis model is:

- Three-dimensional solid elements
- Linear static equilibrium (`*STATIC`)
- Isotropic linear elasticity (`*ELASTIC`)
- Small displacement and small strain. No `NLGEOM`
- Homogeneous temperature and no thermal strain
- One load step and one load case
- Full integration behavior as defined by CalculiX for the chosen element, not a user material routine

Planned element: CalculiX `C3D10`, the 10-node tetrahedron. CalculiX documentation describes it as a general-purpose element with four integration points and recommends quadratic elements for this class of work. Phase 1 must confirm that the generated connectivity is the 10-node element and not a 4-node tetrahedron.

`C3D4` linear tetrahedra may appear only inside a comparison test. They are too stiff to be the model behind a reported safety factor.

Von Mises stress is not a CalculiX output field. CalculiX writes Cauchy stress components. LoadCAD computes:

```text
sigma_vm = sqrt( 0.5 * ((sxx - syy)^2 + (syy - szz)^2 + (szz - sxx)^2)
                 + 3 * (sxy^2 + syz^2 + szx^2) )
```

Component order in the FRD stress block must be confirmed while writing the reader. The expected order to verify is `Sxx, Syy, Szz, Sxy, Syz, Szx`.

Two different stress samples exist:

| Source | What it is | Planned use |
| --- | --- | --- |
| `*EL FILE` / `.frd` | Stress extrapolated to nodes and averaged across elements sharing a node | Contour display, and a candidate decision metric |
| `*EL PRINT` / `.dat` | Integration-point stress | Audit metric, likely closer to the element formulation |

The decision metric chosen on 2026-11-24 is `max_nodal_von_mises`, the maximum nodal von Mises stress with no face exclusion. Section 9 records why the excluded samples were not adopted. `mesh_converged` is false for that study. A solve that is not the stored bracket refinement still writes a null metric and a null safety factor.

If the decision metric exceeds the allowable stress, set `elastic_assumption_exceeded` to true. The linear stress field is then not the expected physical stress field. The ratio still indicates that the load is past the chosen first-yield or allowable check. It is not a collapse load, a reserve factor from a plastic analysis, or a prediction of ultimate failure.

### Supported load cases

Exactly one MVP structural case is a target for verification.

| Item | MVP rule |
| --- | --- |
| Restraint | `encastre_mounting_face`: translations fixed on every node of the matched mounting face. Rotational degrees of freedom are absent on solid elements |
| Load type | Resultant force applied as pressure on `horizontal_top` |
| Direction | Parallel to the face normal, pressing or pulling along that normal. Phase 1 verifies `(0, 0, -1)` |
| Magnitude | Positive scalar in newtons. The pressure magnitude is `force / loaded_face_area` |
| Load set | The matched load-face node or face set, using the solver's own pressure card |

CalculiX pressure on a solid face acts along the face normal. An arbitrary direction is therefore a different feature. The request schema may contain a direction vector so the API does not have to change later, but validation accepts it only when it is parallel to the supported normal within a tolerance. Proposed starting tolerance: absolute cosine with the expected axis at least 0.999. That number is unverified and exists to reject clearly skewed vectors.

Do not distribute an arbitrary force by giving every node an equal share. On a quadratic tetrahedron face, consistent nodal forces for a uniform pressure are not equal, and corner-node contributions can be zero. Equal splitting would preserve a hand-computed resultant while misrepresenting the local traction. Non-normal traction needs its own tested method.

The fixed-face model overstates stiffness relative to screws in holes. Holes on the mounting face remove material. They are not bolt shanks, and they do not carry preload. This sentence belongs in every structural result.

Gravity, acceleration, multiple cases, and follower forces are out of scope.

### Constraint definitions

Geometric checks reject the request before meshing:

- All envelope dimensions and the thickness are finite and positive.
- Thickness is less than length and less than height.
- Fillet radius is finite. For a simulation job it must be strictly positive. A zero-radius inside corner is a singular elasticity problem: refining the mesh raises the peak stress instead of converging it.
- The fillet must fit in the inside corner without consuming either leg. A practical inequality, to be confirmed against the constructor, is that the fillet center and tangent edges remain on both legs and do not cross a hole.
- Hole diameters are finite and positive. Diameter is the in-plane size of a through-hole, not its depth, so it is not required to be smaller than the wall thickness. A hole wider than the wall is still a through-hole.
- The hole must lie inside its assigned leg after the edge margin is applied. It must not intersect the fillet, another hole, or an outer boundary. A cut that leaves more than one solid is rejected.
- Hole centers lie on the requested leg and leave a positive edge margin.
- Holes do not intersect each other.
- Proposed MVP hole count limit: 8. This is a complexity cap, not a structural rule.
- Proposed edge heuristic: the hole wall stays at least one hole-diameter away from a free edge, which places the center at least 1.5 diameters from that edge, and at least one diameter of wall remains between holes. This is a LoadCAD heuristic. It is not a cited fastening code. Replace it if a specific standard is adopted.

Manufacturing checks in the MVP are warnings or request rejections of the kinds above. They do not assess overhangs, bridging, supports, or machine access.

Search constraints:

- Free variables in the first search are thickness and inside fillet radius, each with a user or default minimum and maximum.
- Width, hole pattern, material, restraint type, and load remain fixed during a search unless a later phase adds them to the allow-list.
- A candidate is feasible only when geometry checks pass, the solve completes, the elastic assumption is not exceeded, and the estimated safety factor is at least the target.
- The objective is the smallest CAD volume among feasible samples. If none are feasible, return the samples and state that the target was not met.
- The search result is the best sample among those evaluated. It is not a claim of a global optimum over the continuous ranges.

### Safety factor calculations and limitations

```text
estimated_safety_factor = allowable_stress_MPa / decision_von_mises_MPa
```

Required fields beside the number:

- `allowable_stress_MPa`
- `allowable_basis`: `tensile_yield`, `tensile_strength`, or `specified_allowable`
- `decision_metric`: the name chosen in Phase 2
- `decision_von_mises_MPa`
- `max_nodal_von_mises_MPa`, even when it is not the decision metric
- `elastic_assumption_exceeded`
- `mesh_converged`: true only when a recorded refinement study meets a tolerance that has been written down after being measured
- `restraint`: `encastre_mounting_face`
- `load_model`: `normal_pressure`
- disclaimer id, pointing at the statement that the result is a simulation candidate and is not certified

Target safety factor is a user constraint. Values less than or equal to zero are invalid. A computed safety factor below the target is a feasible-design miss, not a software failure.

Do not report one safety factor for a printed part as if the filament datasheet were the part. Do not hide the raw peak while showing only a filtered stress. Store both when a filtered decision metric exists.

Proposed decision-metric candidates, in the order they should be investigated:

1. Maximum integration-point von Mises stress, excluding elements that touch the fixed face and the loaded face, after a refinement study shows it has stabilized.
2. Maximum averaged nodal von Mises stress with the same exclusion, used for display consistency if it tracks the integration-point metric.
3. A global maximum nodal value, reported always, used as the decision metric only if the refinement study shows it is stable for the filleted bracket.

The exclusion zone is an attempt to separate modeling artifacts at restraints and load patches from the bracket's structural stress. It can also hide a real concentration at a nearby hole. Phase 2 inspected that case before adopting an exclusion. The study did not justify the exclusion, so the decision metric is the unfiltered nodal peak. The result copy keeps the raw peak, says `mesh_converged` is false, and states the singularity risk.

## 6. Core Data Models

These are conceptual records. Do not implement them until the phase that needs them. Names are the vocabulary later code should follow unless this section changes.

### DesignRequest

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | Starts at 1 |
| `part_family` | enum | `l_bracket` only |
| `geometry` | GeometryParameters | Envelope, fillet, holes |
| `material_id` | string | Refers to a versioned card, not a free-text description |
| `load_case` | LoadCase | One case |
| `boundary_condition` | BoundaryCondition | One supported restraint |
| `target_safety_factor` | number | Constraint, must be positive |
| `search` | object or null | Null for a single solve. Otherwise bounds and step for allow-listed variables |
| `notes` | string | Stored and displayed. Never parsed as code or solver input |

### GeometryParameters

| Field | Type | Meaning |
| --- | --- | --- |
| `length_mm` | number | Horizontal leg, outer dimension along X |
| `height_mm` | number | Vertical leg, outer dimension along Z |
| `width_mm` | number | Shared width along Y |
| `thickness_mm` | number | Shared leg thickness |
| `fillet_radius_mm` | number | Inside-corner fillet. Greater than 0 for simulation |
| `holes` | list of Hole | May be empty |

`Hole`:

| Field | Type | Meaning |
| --- | --- | --- |
| `leg` | enum | `vertical` or `horizontal` |
| `diameter_mm` | number | Through-hole diameter |
| `center_across_width_mm` | number | Y coordinate of the center |
| `center_along_leg_mm` | number | Z on the vertical leg, X on the horizontal leg |

Hole count is the length of `holes`. There is no separate count field that can disagree with the list.

### MaterialProperties

| Field | Type | Meaning |
| --- | --- | --- |
| `material_id` | string | Stable id, for example `aluminum_6061_t6` |
| `version` | integer | Increments when any number or citation changes |
| `display_name` | string | UI label |
| `youngs_modulus_MPa` | number | Isotropic modulus |
| `poissons_ratio` | number | Isotropic Poisson ratio |
| `density_tonne_per_mm3` | number | Stored even when unused by the solve |
| `allowable_stress_MPa` | number | Numerator of the safety factor |
| `allowable_basis` | enum | `tensile_yield`, `tensile_strength`, or `specified_allowable` |
| `isotropy` | enum | `isotropic` only in the MVP |
| `source` | string | Citation sufficient to find the datasheet or handbook entry |
| `limitations` | string | Required for printed materials |

### BoundaryCondition

| Field | Type | Meaning |
| --- | --- | --- |
| `type` | enum | `encastre_mounting_face` only |
| `face_role` | enum | `mounting_outer` |
| `dofs` | list | `[1, 2, 3]` fixed at 0. Not user-editable in the MVP |

### LoadCase

| Field | Type | Meaning |
| --- | --- | --- |
| `type` | enum | `normal_pressure_on_face` |
| `face_role` | enum | `horizontal_top` |
| `force_N` | number | Resultant magnitude |
| `direction` | `[number, number, number]` | Unit vector in the global frame |
| `gravity` | boolean | Must be false for the MVP |

### MeshMetadata

| Field | Type | Meaning |
| --- | --- | --- |
| `gmsh_version` | string | From the library that meshed the job |
| `element_type` | enum | `C3D10` for reportable jobs |
| `algorithm` | string or number | The Gmsh 3D algorithm actually selected |
| `element_order` | integer | 2 for reportable jobs |
| `target_size_mm` | number | Requested characteristic length |
| `node_count` | integer | After meshing |
| `element_count` | integer | Volume elements used in the deck |
| `min_quality` | number | Definition recorded, for example minimum SICN |
| `negative_jacobians` | integer | Must be 0 to solve |
| `elements_through_thickness` | number or null | Estimated, when computed |
| `face_matches` | list | Role, Gmsh tags, fingerprint error, uniqueness |
| `bounding_box_error_mm` | number | Imported mesh versus CAD |
| `quality_gate` | enum | `passed` or `failed` |

### SimulationJob

| Field | Type | Meaning |
| --- | --- | --- |
| `job_id` | string | Unique |
| `status` | enum | Lifecycle in section 3 |
| `stage` | enum | Current or last stage |
| `failure_code` | string or null | From the failure table |
| `request` | DesignRequest | Canonical copy |
| `artifact_root` | string | Server-side path. Not client input |
| `created_at` | timestamp | |
| `finished_at` | timestamp or null | |
| `provenance` | object | Section 3 list |

### SimulationResults

| Field | Type | Meaning |
| --- | --- | --- |
| `solver_status` | enum | `completed` or `failed` |
| `max_displacement_mm` | number | Magnitude of the largest nodal displacement vector |
| `max_displacement_node` | integer | Node id in the deck |
| `max_nodal_von_mises_MPa` | number or null | From the FRD field after a successful parse |
| `max_integration_point_von_mises_MPa` | number or null | Present when `.dat` element output was requested |
| `decision_metric` | string or null | Null until Phase 2 selects it |
| `decision_von_mises_MPa` | number or null | |
| `estimated_safety_factor` | number or null | Null on failure and null before the metric exists |
| `elastic_assumption_exceeded` | boolean | |
| `target_met` | boolean or null | |
| `disclaimer` | string | Fixed wording from this document, copied into the result so old jobs stay honest |

### OptimizationIteration

| Field | Type | Meaning |
| --- | --- | --- |
| `iteration_index` | integer | From 0 |
| `parent_job_id` | string | |
| `parameters` | object | Only the free variables, plus the full geometry actually solved |
| `volume_mm3` | number | CAD solid volume |
| `mesh` | MeshMetadata | |
| `results` | SimulationResults | |
| `feasible` | boolean | Section 5 definition |

### ExportArtifact

| Field | Type | Meaning |
| --- | --- | --- |
| `artifact_id` | string | |
| `job_id` | string | |
| `kind` | enum | `step`, `stl`, `msh`, `inp`, `frd`, `dat`, `results_json`, `preview_mesh` |
| `relative_path` | string | Inside the job directory |
| `media_type` | string | |
| `byte_length` | integer | |
| `sha256` | string | |
| `unit` | enum | `mm` for geometry and mesh length. `dimensionless` is not allowed for a CAD file we generated |

`preview_mesh` is a later surface mesh with nodal von Mises values for the viewer. It is derived from solver output. It is not a second analysis.

## 7. CAD and Solver Pipeline

### build123d geometry generation

build123d is the only geometry kernel in the plan. The constructor should:

1. Build the two leg solids in the coordinate system of section 5.
2. Union them.
3. Add the inside fillet on the re-entrant edge produced by the union.
4. Cut through-holes.
5. Check that the result is one solid, with positive volume, and a bounding box equal to the requested envelope within a tight modeling tolerance.
6. Select semantic faces from this final solid by geometric predicates: planar, normal aligned with a global axis, and location consistent with the role.
7. Store a fingerprint per role.

Fingerprint contents:

- Role name
- Centroid in millimetres
- Unit normal
- Surface area in mm²
- Bounding box
- A stable role id from the allow-list, not an Open CASCADE transient index

build123d face labels do not survive being asked for the faces of a solid again. The project maintainers have stated that `faces()` wraps new face objects and that Open CASCADE face objects do not carry the build123d label. STEP export preserves assembly-level names and colors, and it does not provide a reliable `ADVANCED_FACE` name for each face of a finished solid. Discussion #1570 on the build123d repository, dated 2026-11-05, records that limitation. LoadCAD therefore treats fingerprints taken immediately after construction as the identity source, and it re-identifies faces in Gmsh by geometry.

Proposed match tolerances, all unvalidated hypotheses for the first experiment:

| Test | Starting hypothesis |
| --- | --- |
| Centroid distance | 0.05 mm or 0.1 percent of the model diagonal, whichever is larger |
| Normal alignment | Absolute dot product at least 0.999 |
| Area agreement | Within 1 percent |

A role may match one surface or several coplanar fragments. Holes and a STEP import can split the mounting face or the load face. Acceptance requires all of the following:

- Every matched fragment lies on the role's plane and passes the normal test.
- The area-weighted combined centroid and the summed area pass the centroid and area tests against the CAD fingerprint.
- No fragment is a candidate for two roles.
- The role has at least one fragment.

Anything else fails with `face_match_failed`. A one-to-one tag copied from an earlier parameter set is never reused.

Holes add cylindrical faces. Those cylinders get fingerprints too, even though the MVP restraint does not use them, so a later bolted-hole restraint can be tested without inventing a second identity system.

Export:

- `export_step` with millimetre units.
- `export_stl` for the manufacturing artifact. Tessellation tolerances stay in the job metadata. The visualization stress mesh is not this STL, because STL does not carry a nodal stress field.

Also record CAD volume and the final bounding box. The search objective uses that volume.

BREP export is an allowed Phase 1 experiment if STEP import drifts. It is not the primary contract, because BREP drops labels and can be sensitive to Open CASCADE version differences between build123d's bindings and the OCC kernel inside Gmsh. The cadgmsh author's notes on those version mismatches are the reason LoadCAD does not take a hard dependency on an in-memory shape handoff.

### STEP and STL export

| File | Contains | Downstream use |
| --- | --- | --- |
| STEP | Exact solid, millimetres | Gmsh import and user CAD download |
| STL | Triangle approximation, no units, no names | User download for slicing or preview |
| `face_map.json` | Fingerprints | Mesh matching and debugging |

The user-facing STEP and the STEP sent to Gmsh should be the same file, so the analyzed solid is the downloaded solid.

### Gmsh meshing

Planned procedure:

1. Initialize Gmsh without the GUI.
2. Import the STEP file with the Open CASCADE factory.
3. Synchronize.
4. Read the volume bounding box and compare it with the CAD bounding box. Stop on a unit-scale disagreement. A factor near 25.4 or 1000 means a unit conversion happened.
5. Compute center of mass, normal, and area for each surface. Confirm the exact API calls against the installed Gmsh version.
6. Match each role to its surface set using the fingerprint rule above.
7. Create physical groups: a volume group `EALL`, a surface group `FIXED_MOUNT`, and a surface group `LOAD_FACE`.
8. Set a characteristic length from thickness. Starting hypothesis: a size between `thickness / 4` and `thickness / 2`, where the smaller value is the finer mesh. Refinement studies may go finer. Curvature-based sizing should be enabled so the fillet and holes are not represented by a single facet.
9. Generate a 3D mesh of second-order tetrahedra.
10. Optimize the mesh if the installed Gmsh reports inverted elements. A negative Jacobian stops the job.
11. Read nodes, tetrahedra, and group membership through the Gmsh API.
12. Write a `.msh` 4.1 file for debugging and inspection with meshio.

Element type gate:

- Every reportable volume element has 10 nodes.
- The node order is checked once in Phase 1 against the CalculiX `C3D10` convention: corners first, then midside nodes. CalculiX follows the Abaqus corner-then-midside convention. Gmsh's Abaqus export is intended to follow Gmsh's published high-order ordering. A swapped midside node still looks like a mesh and produces a wrong answer, so one reference element must be compared visually or numerically before the writer is trusted.
- Do not freeze `Mesh.SecondOrderIncomplete` from community scripts without checking what it does to tetrahedra in the installed version. That option is primarily about incomplete hex, prism, and quad elements. The gate is "10-node tets with verified order," not a particular option flag copied from a forum.

Quality gates, thresholds unset until the beam study:

- Zero elements with a non-positive Jacobian.
- A recorded minimum element quality.
- Element count above a floor and below a hard cap. Proposed cap for local MVP runs: 200 000 volume elements. This is a workstation guard, not an accuracy target.
- A stated aim of at least two elements through the thickness, revisited when the beam study shows what that aim costs and whether it is enough.

If physical groups are defined, Gmsh file export can omit entities that are not in a group. LoadCAD's writer should take nodes and elements from the API rather than depending on that export behavior.

`cadgmsh` 0.4.0, a MIT-licensed helper for meshing build123d shapes, was current on PyPI as a source distribution during Phase 0 and had very little published usage. It is not a dependency. Phase 1 may try it as a disposable experiment only if direct STEP import fails, and only if this file is updated with the result.

### CalculiX input deck generation

LoadCAD writes the deck. meshio is not the deck writer. meshio's Abaqus reader has historically been sensitive to CalculiX set syntax, and Gmsh's INP export adds headings and surface elements that the solver file does not need.

The deck for the verified case should contain, in substance:

- A node block and a `C3D10` element block, ids consistent between them.
- An element set for the whole volume.
- A node set `FIXED_MOUNT` for the restraint.
- A pressure definition on `LOAD_FACE`. CalculiX applies solid-element pressure with `*DLOAD` and an element face identifier, not with a node set. The writer maps each volume-element face that lies on the matched load surface to the `C3D10` face number published for the installed CalculiX version. Phase 1 takes that numbering from the element figure in that version's manual rather than from memory.
- One `*MATERIAL` and `*ELASTIC` card from the material record, numbers already in MPa.
- One `*SOLID SECTION`.
- One `*STEP` with `*STATIC`.
- `*BOUNDARY` fixing degrees 1, 2, and 3 on `FIXED_MOUNT`.
- A pressure whose integral equals the requested force.
- Output requests for nodal displacement, reaction force (`RF`) on the fixed set, and stress components at the FRD nodal field. Integration-point stress in the `.dat` file is added when the reader for it is implemented.
- No `*INCLUDE`, no user subroutines, and no cards taken from request text.

After a successful solve, sum the reaction components on `FIXED_MOUNT`. They should balance the applied force. Starting hypothesis for the check: each component within 1 percent. This catches a unit error, a bad pressure magnitude, and a model that is not held. It does not prove the load sits on the intended face, because a wrong face with the same resultant still balances. Face identity remains a separate test.

Node ids may be remapped to a dense 1-based sequence. If they are remapped, every set must use the new ids. The mapping file belongs in the job directory.

Phase 1 should prefer a minimal deck that solves the beam. Extra output cards are added when the reader needs them, not before.

### Solver execution

```text
ccx -i job
```

Run this with the working directory set to `solver/`, so the job name is a simple token and the input is `job.inp`. Capture stdout, stderr, the exit code, and wall time. Timeout is a product setting. Starting hypothesis: 10 minutes for MVP meshes, shortened if the element cap makes long runs unnecessary. Kill the process on timeout and mark `solver_timeout`.

Interpret failure if any of these occur:

- Nonzero exit status
- No `.frd` file after a requested successful solve
- Solver log text indicating an error or a singular system
- A result file that the reader cannot parse

Do not scan logs with an open-ended rule that treats the word "error" inside a path as a failure without checking real CalculiX output first. Phase 1 should record actual failure text and then lock the patterns.

The Windows binary is an open setup task. Sources identified in public documentation on 2026-11-22, none of them downloaded here:

| Source | What was published | Phase 0 status |
| --- | --- | --- |
| conda-forge `calculix` 2.22 win-64 | Package page timestamp 2025-01-07, license GPL-2.0-or-later | Not installed. Conda itself is not installed |
| `https://www.dhondt.de/calculix_2.22_4win.zip` | Cited by participants on the CalculiX discourse on 2025-09-23 as a Windows build | URL not fetched and not run |
| Official CalculiX manual | Version 2.21 manual PDF at `dhondt.de` | Used as the behavior reference. Confirm against the binary that is actually installed; 2.22 may differ |

An old 2.10 Windows bundle from 2016 is not the target. Prefer a current 2.22 `ccx` once its origin and checksum are recorded.

Phase 1 chooses one binary, records its version banner and checksum, and uses that path from configuration.

### Result extraction

Reader plan:

1. Confirm the solve produced the expected files.
2. Parse nodal displacements and record the maximum displacement magnitude and node.
3. Parse Cauchy stress.
4. Compute von Mises stress with the formula in section 5.
5. Store the raw maxima even before a decision metric exists.
6. Refuse to emit `estimated_safety_factor` until `decision_metric` is set in this document and the code.

meshio's published format list includes Gmsh `.msh` and Abaqus `.inp`. It does not list CalculiX `.frd`. The FRD or DAT reader should be small, covered by a fixture taken from a real `ccx` run, and limited to the cards LoadCAD requests. A third-party FRD converter such as `ccx2paraview` may be evaluated later. It is not adopted. Its license and maintenance would need a review before it became a dependency.

For the viewer, a later step extracts the surface triangles and the already computed nodal scalars into `preview_mesh`. Three.js colors that field. It does not calculate a second safety factor.

### Optimization loop

Phase 3 only. The loop is a deterministic search, not a topology optimizer and not a call to an untested black-box solver.

Planned first algorithm: a documented grid or coordinate walk over thickness and fillet radius, using fixed steps from the request. Evaluate every point by running the full geometry–mesh–solve path. Stop when the grid is finished or when a configured evaluation cap is hit. Starting cap hypothesis: 12 solves. Choose the feasible sample with the smallest CAD volume.

Every iteration is retained, including infeasible and failed ones. A failed mesh at one point does not erase previous points. The search result lists the winner separately from the log.

SciPy optimizers are unnecessary for a two-variable grid. Revisit them only if the allow-listed variable count makes a grid wasteful and the objective has been shown to be stable under mesh refinement. An optimizer wrapped around a noisy, singular stress peak will manufacture false precision.

## 8. Technology Decisions

### Chosen technologies

| Piece | Choice | Why it is in the plan |
| --- | --- | --- |
| CAD | build123d | Parametric Python solids, STEP and STL export, Apache-2.0, active documentation. Default model unit is millimetres |
| CAD kernel | Open CASCADE through build123d's separate bindings | Required by build123d. LGPL-2.1 plus the OCCT exception when the pip wheel stays replaceable |
| Mesher | Gmsh Python API | STEP/OCC import, physical groups, tetrahedral meshing, local and scriptable. Official install path includes `pip install gmsh` |
| Solver | CalculiX `ccx` | Free GPL solver, Abaqus-like deck, 3D solid elements, linear static analysis, Windows builds exist |
| Arrays | NumPy | Mesh tables and von Mises math |
| Mesh inspection | meshio | Read `.msh`, convert debugging meshes. MIT |
| Later API | FastAPI and Pydantic | Typed boundary around an already working function |
| Later UI | React, TypeScript, Vite, React Three Fiber, Tailwind | Ordinary web stack for a 3D review page |
| MVP storage | Job directories, then SQLite | Matches the file-shaped artifacts and the single-user start |

### Alternatives considered

| Alternative | Why it is not the MVP path |
| --- | --- |
| CadQuery as the CAD API | Capable and also on Open CASCADE. build123d is the selected Python API. Switching would be a documented change, not a silent one |
| FreeCAD headless | Heavier application dependency for the same class of kernel |
| Gmsh as the solid modeler | Would duplicate the CAD model in a second description and weaken the STEP artifact the user downloads |
| `cadgmsh` | Convenient, immature as a project dependency, and unnecessary if STEP import works |
| CalculiX GraphiX (`cgx`) as the product UI | Useful for humans debugging a deck. The product preview is a web view of stored fields |
| Code_Aster or Elmer | Credible solvers with a larger integration and operations burden for a first linear-static bracket |
| FEniCSx or SfePy | Good research libraries. They would make LoadCAD own element formulations that CalculiX already provides |
| Linear tetrahedra as the default | Excessively stiff for stress-driven bracket decisions |
| MongoDB or Atlas | Extra service, file artifacts fit it poorly, and a free database tier does not run FEA. The server license is SSPL |
| Celery and Redis | Two more services for a queue of one local process |
| Equal nodal `*CLOAD` for pressure | Inconsistent with quadratic face load distribution |
| User-uploaded STEP in the first release | Breaks the "we know the faces" assumption and widens the untrusted-file problem |
| Cloud free tier as the first runtime | CPU, disk, and process lifetime are a poor match for meshing and solving |

### Tradeoffs

- **Gmsh in-process versus Gmsh as a separate program.** The Python API is the practical local interface and is what Phase 1 should use. It loads a GPL library into the process. A separate `gmsh` process is a cleaner distribution boundary and a worse development experience. Phase 1 may use the Python API. A proprietary shipment has to revisit this before release.
- **Our own deck writer versus Gmsh INP export.** Writing the deck is more code and gives control over sets, units, and element order. Depending on Gmsh's exporter is shorter and has known cleanup problems. Control wins.
- **Fillet required versus literal sharp L.** A sharp model is easier to construct and a poor stress model. Simulation requires a fillet. Users who want a sharp solid for manufacturing can be offered a geometry-only export later; that export must not carry a safety factor.
- **Fixed face versus fixed holes.** The face restraint is identifiable and reproducible. It is a worse model of screws. Holes are still generated so the geometry matches the part the user will make.
- **Normal pressure only versus arbitrary direction.** Arbitrary direction was requested and is represented in the schema. Shipping it without a tested traction model would create confident, wrong load vectors. Validation rejects it for now.
- **Grid search versus continuous optimization.** The grid is explainable and reproducible. It can miss a better point between samples. The result copy has to say that.
- **Local files versus a database.** Files are inspectable by a mechanical engineer with a text editor and `ccx`. They are a weaker query API. SQLite can index them later without moving the blobs.

### Open questions

| ID | Question | Blocks |
| --- | --- | --- |
| Q1 | Which Windows `ccx` 2.22 binary runs on this machine, and what is its checksum? | Answered 2026-11-23. See below |
| Q2 | Does STEP import preserve millimetres with the installed build123d and Gmsh pair? | Answered 2026-11-23 for the beam and the Phase 1 bracket. See below |
| Q3 | Do the proposed fingerprint tolerances uniquely match bracket faces after holes and a fillet? | Answered 2026-11-23 for the Phase 1 fixture. Not a sweep of every legal bracket |
| Q4 | Does Gmsh's 10-node tet connectivity match CalculiX `C3D10` on one inspected element? | Answered 2026-11-23. Raw Gmsh order does not match. `swap_last_two` does |
| Q5 | What displacement and stress differences remain between a slender cantilever solid model and Timoshenko beam theory after refinement? | Answered 2026-11-24 for sizes 5, 2.5, and 1.25 mm. Displacement is inside the 5% candidate. No stress band is adopted |
| Q6 | Which von Mises sample becomes `decision_metric`? | Answered 2026-11-24. `max_nodal_von_mises`. Exclusion was not adopted |
| Q7 | What mesh-convergence band is acceptable for that metric? | Answered 2026-11-24. No stress band is adopted. `mesh_converged` is false |
| Q8 | Which cited numbers go into the first aluminum, PLA, and PETG cards? | Answered 2026-11-24. Cards are version 1 in `backend/src/loadcad/materials/cards.py`. Only aluminum is solvable |
| Q9 | Does the user-profile space in `C:\Users\Martin Tran` break `ccx` or Gmsh if the job directory stays under the repository? | Answered 2026-11-23 for a box mesh and a one-tet solve. It did not break those runs |
| Q10 | Project license, and is the Gmsh Python API acceptable for the intended distribution? | Before any proprietary release. Not a Phase 1 code blocker |
| Q11 | What minimum fillet radius still meshes with a stable stress result for the allowed thickness range? | Not established. Radius 0 is rejected before meshing. The only refined radius is 3 mm, and its stress did not flatten |
| Q12 | Does a hole near the fillet make a face-exclusion stress metric unconservative? | Answered 2026-11-24 for one legal hole at the fillet clearance. Exclusion lowered the 2.5 mm nodal peak and left the 1.25 mm peaks unchanged. Exclusion was not adopted |

### License considerations

| Component | License observed in public sources | Planning consequence |
| --- | --- | --- |
| build123d | Apache-2.0 | Compatible with a permissive or copyleft project license |
| Open CASCADE bindings used by build123d | LGPL-2.1 with the OCCT exception | Keep the published wheel replaceable. Ship its license notice if binaries are redistributed. Recheck if a packager freezes it into a single static executable |
| Gmsh | GPL-2.0-or-later, with an exception intended to ease linking with external libraries. The project states that this GPL build cannot be integrated into distributed closed-source software. A commercial license is available from the Gmsh authors | Phase 1 local use is fine. Closed-source distribution is an unresolved legal issue |
| CalculiX | GPL-2.0 | Run the unmodified executable as a separate process. Do not vendor its source into LoadCAD |
| meshio | MIT | Low friction |
| NumPy, FastAPI, Pydantic, React, Three.js, Vite, Tailwind | Permissive licenses, to be reconfirmed when pinned | Acceptable |
| SQLite | Public-domain style dedication | Acceptable |
| MongoDB server | SSPL, not an OSI-approved license | Unused in the MVP |

No `LICENSE` file is added in Phase 0. The documents are not released under an open-source license by being stored in a Git repository.

### Architecture decision records

**ADR-001. One part family.**  
The MVP models only a filleted L-bracket with a shared thickness and a constrained hole list. A general CAD agent would be impossible to verify with the first benchmarks.

**ADR-002. build123d is the solid modeler.**  
It exports the STEP file the user receives and the STEP file the mesher imports. Face identity is a fingerprint, not a kernel label.

**ADR-003. Gmsh is the mesher.**  
Physical groups are created after geometric matching inside Gmsh. The Python API is approved for local development, with the GPL distribution question left open.

**ADR-004. CalculiX is the solver, used only for linear static elasticity in the MVP.**  
`ccx` runs as an unmodified subprocess. LoadCAD writes the deck and reads the results.

**ADR-005. Files first, SQLite second, no MongoDB in the MVP.**  
Mesh and result artifacts are files. A database is an index, added with the API. Atlas does not solve the compute problem, and the document model does not remove the need for a job directory.

**ADR-006. No Celery.**  
One subprocess and a status file cover local execution. A broker is justified only by concurrent multi-user demand that does not yet exist.

**ADR-007. No web tier before a beam benchmark.**  
FastAPI and React are accepted as later phases. They are not Phase 1 scaffolding.

**ADR-008. Reportable models use `C3D10`, isotropic linear elasticity, and a post-processed von Mises metric.**  
The metric's exact sampling rule remains Q6. The element family and the constitutive model do not.

**ADR-009. Normal pressure on one face is the only load that can be reported.**  
Arbitrary directions stay invalid until a separate method is verified.

**ADR-010. The license is deliberately unset.**  
Choosing Apache-2.0 or GPL-2.0-or-later before the Gmsh packaging decision would pretend the legal question is settled.

## 9. Development Phases

A phase starts only when the previous phase's exit criteria are recorded in this file and the user has approved the next phase. Do not start Phase 1 from this document alone; the approval is a separate message.

### Phase 0: Documentation and planning

**Work:** `README.md` and `CONTEXT.md`.

**Exit criteria:** Both files exist, they agree on scope, units, stack, and phase gates, and they do not claim a simulation was run.

**Status:** Completed on 2026-11-22, subject to review of these two files. No code was added.

### Phase 1: Local headless CAD, Gmsh, and CalculiX proof

**Goal:** Prove the toolchain on this Windows machine with a known beam, then generate one hard-coded filleted L-bracket and carry it through mesh and solve.

**In scope:**

- Project virtual environment and pinned numerical dependencies
- A recorded `ccx` binary
- A rectangular cantilever constructor and the L-bracket constructor
- STEP and STL for the bracket
- Gmsh import, face match, `C3D10` mesh, and a project-written deck
- One successful `ccx` run for the beam and one for the bracket
- Parsed maximum displacement and maximum nodal von Mises stress, stored as uncertified output
- Tests that fail if the unit bounding box is off by a scale factor, if the face match is ambiguous, or if the solver result files are missing

**Out of scope:** Materials library beyond constants needed for the beam, safety-factor decisions, search, HTTP, database, UI, Docker, and user-facing installation docs that pretend the flow is productized.

**Exit criteria:**

1. A fresh virtual environment, documented by the lockfile that Phase 1 actually creates, can run the proof.
2. The beam test prints or stores displacement error against Euler-Bernoulli and Timoshenko formulas, with E, nu, L, b, h, P, element size, and node count.
3. The error is measured, not assumed. This file is updated with the measured error and the tool versions. No pass band is invented before that measurement.
4. The bracket job directory contains STEP, STL, mesh, `.inp`, solver output, and a results JSON.
5. Face match either succeeds uniquely or fails the test. A silent wrong face is a failed phase.
6. `C3D10` node order is either confirmed on a sample element or listed as a remaining blocker that prevents stress from being treated as meaningful.
7. README status stays pre-MVP and does not claim a validated design method.

**Status:** Completed on 2026-11-23 for the fixture below. Those two jobs emitted no safety factor. The refinement and the safety-factor record are in the Phase 2 section. No stress pass band was declared from the single 5 mm mesh.

#### Environment that ran the proof

| Item | Measured value |
| --- | --- |
| Python | 3.12.6, virtual environment `.venv`. Dependencies were not installed into the global interpreter |
| Lockfile | `backend/requirements.lock`, a `pip freeze` of that environment with the editable `loadcad` line removed. Direct requirements are build123d 0.13.0, gmsh 4.15.2, meshio 5.3.5, numpy 2.5.5, and pytest 9.2.0. build123d pulled scipy 1.18.1 and scikit-learn 1.9.1. LoadCAD does not import them |
| Platform | `Windows-11-10.0.26300-SP0` |
| `ccx` | `tools/calculix/dist/calculix_2.22_4win/ccx_static.exe`. The process banner, read from stdout because `job.dat` is only the `*NODE PRINT` table, is `CalculiX Version 2.22, Copyright(C) 1998-2024 Guido Dhondt`. The FRD header says `Version 2.22`. The same header reports compile time `Sun Aug  4 19:39:24     2024`. The log reports PaStiX 6.0.1. `OMP_NUM_THREADS=1` |
| Checksums | Zip `https://www.dhondt.de/calculix_2.22_4win.zip` SHA-256 `a1f91281944c96d6cd914cc020421e8ae65973b3e15d055dc63a3e3e3066d281`. `ccx_static.exe` SHA-256 `a326dfb2efe888e35e2195da263761c0b646b10e452b8998f36ea38da612a277` |
| Binary not used | `ccx_dynamic.exe` is in the same directory. Its `README_Install` says it needs `mkl_rt.2.dll`, which the zip does not contain. That executable was not run. Invoking `ccx` with no arguments prints a usage line and exits 201, so that output was not used as the version |

A UTF-8 BOM at the start of the lockfile was removed on 2026-11-23. It would have made the first package name invalid to pip. After that fix, a new virtual environment at `C:\Temp\loadcad-phase1\venv-lock` installed the lockfile, and the same 22 tests passed there in 17.22 seconds. That run used the source tree on `PYTHONPATH`. It did not reinstall the editable `loadcad` package, because the lockfile intentionally omits that line.

#### Q1 and Q9

Q1 is the static binary, path, banner, and checksums above. Q9: Gmsh 4.15.2 wrote a box mesh, and `ccx_static` solved a one-element deck, in both `C:\Users\Martin Tran\Documents\loadcad\artifacts\phase1\path-with-space` and `C:\Temp\loadcad-phase1\path-nospace`. Both `ccx` runs returned 0 and wrote an FRD file. The beam and bracket jobs then ran under the repository path, which contains a space.

#### Q4, node order

Gmsh 4.15.2 `getElementProperties(11)` reports tetrahedron 10 reference coordinates:

| Gmsh node | Reference coordinate | CalculiX `C3D10` role |
| --- | --- | --- |
| 1 | (0, 0, 0) | corner 1 |
| 2 | (1, 0, 0) | corner 2 |
| 3 | (0, 1, 0) | corner 3 |
| 4 | (0, 0, 1) | corner 4 |
| 5 | (0.5, 0, 0) | midside 1-2 |
| 6 | (0.5, 0.5, 0) | midside 2-3 |
| 7 | (0, 0.5, 0) | midside 3-1 |
| 8 | (0, 0, 0.5) | midside 1-4 |
| 9 | (0, 0.5, 0.5) | midside 3-4, which is CalculiX node 10 |
| 10 | (0.5, 0, 0.5) | midside 2-4, which is CalculiX node 9 |

The raw Gmsh connectivity is therefore not CalculiX order. The map `swap_last_two`, indexes `(0, 1, 2, 3, 4, 5, 6, 7, 9, 8)`, is the first candidate that a straight tetrahedron in each proof mesh satisfied. That same map was applied to every element, including curved ones. Curved midside nodes are not chord midpoints, so they were not used to choose the map. Both result files store `c3d10_raw_gmsh_order_matches: false` and metadata `c3d10_node_order: "swap_last_two"`.

Surface triangles use Gmsh type 9 order: three corners, then midsides of edges 1-2, 2-3, and 3-1. `getElementProperties(9)` returns those six nodes as parameter pairs, not as the garbage that a 3-D reading of the same array produces. Each proof mesh required at least one straight face triangle to match that order before the curved triangles were accepted.

#### Q2, units

The Phase 1 bracket STEP file contains the tokens `MILLI` and `METRE`. That check is in `backend/tests/test_geometry.py`, and that test passed. Gmsh import uses millimetre target units. The imported bounding boxes agree with the CAD boxes well inside the 0.05 mm scale gate. The stored bracket mesh box is about `-1e-7` to `60.0000001` mm against CAD `(0, 0, 0)` to `(60, 30, 60)`. The cantilever box has the same `1e-7` mm noise. A short beam, length 40 mm and element size 4 mm, is asserted within `1e-4` mm.

#### Q5, one cantilever mesh

This is one mesh, not a refinement study. No pass band is declared.

| Input | Value |
| --- | --- |
| Section | 10 mm by 10 mm, length 200 mm, centered on Y and Z, X from 0 to 200 |
| Material used for the solve | E = 210000 MPa, nu = 0.3. Benchmark placeholder, not an approved card |
| Tip load | 100 N in -Z, as consistent `C3D10` nodal forces on the tip face. Not a pressure |
| Element size | 5 mm |
| Mesh | 1839 nodes, 794 `C3D10` elements, minimum SICN 0.328 |
| Tip sample | Node 390, nearest the tip center. `uz = -1.51964` mm. Downward deflection 1.51964 mm |
| Euler-Bernoulli tip | 1.5238095238095237 mm. Relative error `(FEA - theory) / theory = -0.0027362499999998777` |
| Timoshenko tip | 1.5267809523809523 mm, shear coefficient 6/5. Relative error `-0.004677129597285207` |
| Midspan axial sample | Beam theory `sxx` magnitude 60 MPa. Mean of 22 top samples 59.847759090909086 MPa. Mean of 22 bottom samples -59.90078181818182 MPa. Informational, not a pass/fail |
| Peak nodal von Mises | 121.5676136507051 MPa at node 1176. Stored only. Not a decision metric |
| Fixed-face reactions | Sum about `(0, 0, 100)` N. `reaction + applied` residual relative to 100 N is `8.51098701878659e-06` |
| CalculiX time | 0.214586 s in the stored solver log. This is CalculiX's own timer for that run, not the meshing time |

The opening block of `ccx.log` says its element count is an estimated upper bound. That line says 822 elements. The deck contains 794 `C3D10` records. The deck contains no `*MPC` card.

#### Q3 and the bracket solve

Fixture: length 60 mm, height 60 mm, width 30 mm, thickness 5 mm, fillet radius 3 mm, one 5 mm vertical hole and one 5 mm horizontal hole, 100 N in `(0, 0, -1)`, element size 2.5 mm, same placeholder E and nu. `allowable_stress_mpa`, `target_safety_factor`, `decision_metric`, and `estimated_safety_factor` are null.

| Result | Measured value |
| --- | --- |
| CAD volume | 17111.59295503332 mm³ |
| Face match | `mounting_outer` tag 8 only, `horizontal_top` tag 7 only. The sets are disjoint |
| Mesh | 12576 nodes, 6769 `C3D10` elements, minimum SICN 0.151 |
| Pressure | 0.06481312214663258 MPa on 1542.8974363210118 mm² of corner-triangle area, so the requested resultant is 100 N |
| Peak displacement | 0.03503132794317959 mm at node 574 |
| Peak nodal von Mises | 22.978311865007452 MPa at node 2223. Not a decision metric |
| Fixed-face reactions | Z component 99.83760273861984 N. `reaction + applied` leaves -0.16239726138016408 N in Z. Relative residual 0.001623972744233981. X and Y residuals are about 1e-4 N or smaller |
| CalculiX time | 1.087509 s in the stored solver log. This is CalculiX's own timer for that run, not the meshing time |

The bracket residual is a load check. It does not prove which face was loaded. The fingerprint match is the face-identity evidence. The residual was not isolated further. One candidate is the difference between corner-triangle area and the quadratic face area CalculiX integrates around the hole. That split was not measured separately.

The solver log's estimated upper bound says 8173 elements. The deck contains 6769 `C3D10` records.

Job directories `artifacts/phase1/beam` and `artifacts/phase1/bracket` contain the request, status, provenance, geometry log, Gmsh log, CalculiX log, STEP, STL, face map, mesh, mesh metadata, `job.inp`, `job.frd`, `job.dat`, `job.sta`, and `results/results.json`. Both statuses are `completed`. A stale beam `failure.log` from an earlier FRD parse error was removed after the successful rerun. The parser now accepts CalculiX 12-character fields, including a leading minus glued to the previous field, and reads reactions from the `FORC` block (`F1`, `F2`, `F3`) that `*NODE FILE` writes for `RF`.

Mesh files are Gmsh 2.2. meshio 5.3.5 rejected a Gmsh 4.1 file that carried physical groups, with incompatible cell data `gmsh:physical`. The 2.2 short-beam file was read successfully.

#### What Phase 1 does not claim

The cantilever is one mesh size. The bracket has no closed-form stress result. Nodal von Mises values are post-processed from FRD stress components. They are not a safety factor, not a certified stress, and not evidence that the design is adequate. README status stays pre-MVP.

### Phase 2: Materials, boundary conditions, and simulation validation

**Goal:** Turn the proof into a defined structural estimate for the one supported load case.

**In scope:** Versioned material cards with citations, the restraint and pressure models, integration-point and nodal metrics, mesh-refinement studies, the choice of `decision_metric`, and rejection rules for singular geometry.

**Exit criteria:** Q6, Q7, and Q8 are answered in this file. A bracket refinement study is stored. Safety-factor output includes every field in section 5. At least one intentionally bad model, such as a fully unconstrained solid or a zero fillet, fails cleanly.

**Status:** Recorded on 2026-11-24. Q6, Q7, and Q8 are answered below. The bracket study is in `backend/studies/phase2_bracket.json`. The safety-factor record is in that file and is copied here. A zero fillet and an unrestrained solid fail without a safety factor. `mesh_converged` is false. This is not a certified design.

The same CalculiX 2.22 `ccx_static.exe`, Gmsh 4.15.2, and project virtual environment as Phase 1 were used. `OMP_NUM_THREADS=1`. Beam jobs use the Phase 1 benchmark constants, E = 210000 MPa and nu = 0.3, so the comparison with beam theory stays on those constants. Bracket jobs use `aluminum_6061_t6` version 1. The deck material token stays `BENCHMARK`. The card id is stored only in JSON.

#### Q8, material cards

| Card | Version | E | nu | Density | Allowable | Basis | Solvable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `aluminum_6061_t6` | 1 | 68900 MPa | 0.33 | 2.7e-9 tonne/mm³ | 276 MPa | `tensile_yield` | Yes |
| `prusament_pla` | 1 | 2300 MPa | none | 1.24e-9 tonne/mm³ | 17 MPa | `specified_allowable` | No |
| `prusament_petg` | 1 | 1500 MPa | none | 1.27e-9 tonne/mm³ | 18 MPa | `specified_allowable` | No |

Aluminum values are the Aluminum Association typical numbers on the ASM MatWeb 6061-T6 sheet, bassnum MA6061t6, read 2026-11-24: tensile yield 276 MPa, modulus 68.9 GPa, density 2.70 g/cm³. The sheet marks Poisson's ratio 0.33 as estimated from similar aluminum alloys. The card limitations say the AA data are not for design, are not an MMPDS A-basis or B-basis allowable, and do not specify product form. Source URL: `https://asm.matweb.com/search/SpecificMaterial.asp?bassnum=MA6061t6`.

PLA and PETG numbers are from the Prusa Polymers technical datasheets, version 1.1, last update 16-02-2022. The moduli are the horizontal ISO 527-1 values, 2.3 GPa and 1.5 GPa. Densities are ISO 1183, 1.24 g/cm³ and 1.27 g/cm³. The allowables are the published interlayer adhesions, 17 MPa and 18 MPa, not the horizontal tensile yields of 51 MPa and 47 MPa. Those sheets do not give Poisson's ratio. `require_solvable()` raises `request_invalid` for both cards. A Poisson ratio from a different paper is not copied onto these cards.

#### Q5, cantilever refinement

Three meshes of the Phase 1 cantilever. Outer-fiber beam-theory stress is `P L (h / 2) / I` = 120 MPa. Tip formulas are unchanged: Euler-Bernoulli 1.5238095238095237 mm, Timoshenko 1.5267809523809523 mm. No stress pass band is declared.

| Element size | Nodes | Elements | Tip, mm | Error vs Timoshenko | Max nodal, MPa | Max IP, MPa | Excluded nodal, MPa | Excluded IP, MPa | Min SICN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 mm | 1839 | 794 | 1.51964 | -0.004677129597285207 | 121.5676136507051 | 109.24148277726334 | 121.5676136507051 | 101.8006627542037 | 0.32813709407741276 |
| 2.5 mm | 13203 | 7233 | 1.52073 | -0.003963209241978178 | 119.96376682141755 | 119.05565641793889 | 119.96376682141755 | 110.36846845905566 | 0.3006060505828765 |
| 1.25 mm | 78548 | 49705 | 1.52129 | -0.003596424472279015 | 143.87843461812025 | 141.78288267049717 | 124.36086036271848 | 112.92418529950022 | 0.2899750654703822 |

The finest tip error against Timoshenko is -0.003596424472279015. That is inside the 5% displacement candidate named before this table existed. The last refinement changed the tip by relative 0.00036824419851000243. This displacement check is not a stress band.

At 1.25 mm the global nodal peak is node 2 at `(0, -5, 5)` mm, a corner of the fixed face, 143.87843461812025 MPa. Relative to the 120 MPa fiber stress that is +0.1989869551510021. The excluded nodal peak is node 14842 at `(0.91506350946, -4.0849364905, -5)` mm, 124.36086036271848 MPa, relative +0.03634050302265403. The excluded integration-point peak is 112.92418529950022 MPa, relative -0.05896512250416481. The last refinement raised the global nodal peak by relative 0.19934909039912818 and the excluded nodal peak by relative 0.03665351345499685. The fixed-face corner is a restraint sample. The inboard outer-fiber sample is closer to 120 MPa and is still moving. Neither is given a pass band.

Fixed-face reaction balance on these three beam meshes stays near 1e-5 relative. The full rows are in `backend/studies/phase2_beam.json`. Peak coordinates are in `backend/studies/phase2_peaks.json`.

#### Bracket refinement and the reaction residual

Same geometry as the Phase 1 bracket. Material `aluminum_6061_t6`. Pressure is `100 N / quadratic_triangle_area` of the loaded face. The corner-triangle area is stored beside it. Sizes 5, 2.5, and 1.25 mm. Element counts stayed under the 200000 cap.

| Element size | Nodes | Elements | Max displacement, mm | Max nodal, MPa | Max IP, MPa | Excluded nodal, MPa | Excluded IP, MPa | Reaction Z, N | Relative balance | Min SICN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 mm | 3968 | 1934 | 0.10347511935372701 | 19.853864631903914 | 22.099496423517007 | 18.0129013191072 | 15.773872299600562 | 99.95948057750002 | 0.00040519641560245965 | 0.035646673132626865 |
| 2.5 mm | 12576 | 6769 | 0.1059448646182312 | 23.040293747204462 | 20.433328583680886 | 18.565897065113926 | 16.67525306079077 | 99.9593433441401 | 0.00040657148500031367 | 0.15056475954249293 |
| 1.25 mm | 71081 | 43487 | 0.1065433514224539 | 25.876673219034874 | 23.34072181593601 | 25.731386260105715 | 23.34072181593601 | 99.98777679260431 | 0.00012223954524946782 | 0.2886104548236977 |

Last-step relative changes, from 2.5 mm to 1.25 mm: displacement +0.005649040247295845, nodal von Mises +0.12310517838664957, integration-point von Mises +0.1422868144242108, excluded nodal +0.38594898861396976, excluded integration-point +0.39972219497034445.

On the 1.25 mm mesh the nodal peak is node 7794 at `(7.4370779821, 11.567835638, 5.0532867799)` mm. The excluded nodal peak is node 7786 at `(6.7683422976, 16.261784874, 5.264489206)` mm. Both sit at the inside fillet, and their hole-wall distances are 30.243299200758642 mm and 30.755603658863414 mm. The Phase 1 holes are not the peak. The integration-point peak and the excluded integration-point peak are the same element, 46549. The mean of that element's four corner nodes is `(6.3068335739500005, 17.58766504475, 5.266393432225)` mm, which is also in the fillet region and is not the integration-point coordinate. Exclusion removed 13247 of 43487 elements and did not change the integration-point peak. It lowered the nodal peak only from 25.876673219034874 MPa to 25.731386260105715 MPa.

The 5 mm and 2.5 mm excluded nodal peaks, 18.0129013191072 MPa and 18.565897065113926 MPa, looked quiet and then jumped on the next refinement. That pair is not evidence that the excluded metric had converged. At 5 mm, 1649 of 1934 elements touch the fixed or loaded face, and the minimum SICN is 0.035646673132626865. There is no SICN rejection threshold in the code. The solve was kept and the low quality is part of the record.

Quadratic loaded area and corner-triangle area:

| Element size | Pressure faces | Quadratic area, mm² | Corner area, mm² | Pressure, MPa |
| --- | --- | --- | --- | --- |
| 5 mm | 269 | 1541.0175864136068 | 1542.8974363210118 | 0.0648921860994 |
| 2.5 mm | 671 | 1541.0175864136068 | 1542.8974363210118 | 0.0648921860994 |
| 1.25 mm | 2437 | 1540.555602276636 | 1541.1206211357219 | 0.06491164606601658 |

The 5 mm and 2.5 mm areas match in the stored JSON while the face counts do not. A planar face area depends on its boundary nodes. The boundary sets were not compared node by node.

Phase 1, using corner-triangle pressure on the 2.5 mm bracket, stored a Z shortfall of 0.16239726138016408 N. The Phase 2 2.5 mm job, using quadratic-triangle pressure and the aluminum card, stored reaction Z 99.9593433441401 N, shortfall 0.0406566558599053 N. On that mesh the corner area exceeds the quadratic area by 1.8798499074050596 mm². Times the quadratic pressure, that difference is 0.121987570030269 N. Subtracting it from the Phase 1 shortfall leaves 0.04040969134989508 N, which is 0.0002469645100102169 N away from the Phase 2 shortfall. The two jobs also differ in modulus, Poisson's ratio, and the mesh that Gmsh produced. The area split is consistent with most of the old gap. It does not close the residual. At 1.25 mm the shortfall is 0.01222320739569227 N. At 5 mm it is 0.04051942249998319 N.

#### Q6 and Q7

Candidate 1 was the maximum integration-point von Mises stress on elements that do not touch the fixed face or the loaded face. On this bracket that sample went 15.773872299600562, 16.67525306079077, then 23.34072181593601 MPa. The last step is relative +0.39972219497034445. It has not stabilized, so it is not the decision metric.

Candidate 2, the excluded nodal peak, rose by relative +0.38594898861396976 on the same step. It is not the decision metric either.

Candidate 3 is the global nodal peak. It is the decision metric because the exclusion was not justified and this is the unfiltered value. On the finest bracket mesh it is also the largest of the four samples. The name in the result file is `max_nodal_von_mises`.

`mesh_converged` is true only when a stress band has been written down after a study that meets it. `STRESS_RELATIVE_BAND` in `backend/src/loadcad/postprocess/decision.py` is `None`. The 5% figure remains the beam-tip displacement candidate, which the finest cantilever meets. It is not copied onto stress. Widening a stress band until the +0.12310517838664957 nodal change or the +0.39972219497034445 excluded change would pass was not done. `mesh_converged` is false.

#### Safety-factor record

The record is for the 1.25 mm aluminum bracket in the three-size study, not for the near-hole probe and not for the beam. `estimated_safety_factor` = 276 / 25.876673219034874 = 10.665976946254995.

| Field | Value |
| --- | --- |
| `allowable_stress_mpa` | 276.0 |
| `allowable_basis` | `tensile_yield` |
| `decision_metric` | `max_nodal_von_mises` |
| `decision_von_mises_mpa` | 25.876673219034874 |
| `max_nodal_von_mises_mpa` | 25.876673219034874 |
| `estimated_safety_factor` | 10.665976946254995 |
| `elastic_assumption_exceeded` | false. 25.876673219034874 is below 276 |
| `mesh_converged` | false |
| `restraint` | `encastre_mounting_face` |
| `load_model` | `normal_pressure` |
| `disclaimer` | Simulated linear-elastic candidate under the stated assumptions. Not a certified, physically tested, or guaranteed-safe design |

The card limitations are stored on the same object. They say the Aluminum Association typical values are not for design. The factor is an unconverged linear-elastic ratio for this mesh, this restraint, and this pressure. It is not a certification, not a plastic reserve, and not evidence that the bracket is adequate.

#### Q12, hole at the fillet clearance

The product rule rejects a hole whose center is closer than thickness + fillet + radius. For this bracket that limit is 10.5 mm. A separate pair of solves moved the horizontal hole from x = 40 mm to x = 10.5 mm and left the vertical hole at z = 40 mm. Material and load match the bracket study. Sizes 2.5 mm and 1.25 mm. Stored in `backend/studies/phase2_near_hole.json`. This pair is not the safety-factor fixture.

| Element size | Elements | Max nodal, MPa | Excluded nodal, MPa | Max IP, MPa | Excluded IP, MPa | Peak node, mm | Hole-wall distance, mm | Min SICN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.5 mm | 6753 | 38.50734963193995 | 37.48549252414195 | 35.1882236997135 | 35.1882236997135 | (10.50002864, 17.5, 5.0) | 1.7763568394002505e-15 | 0.09267682413528726 |
| 1.25 mm | 43405 | 39.79050421914956 | 39.79050421914956 | 36.47052481391922 | 36.47052481391922 | (10.198658299, 12.518227815, 0.0) | 4.440892098500626e-16 | 0.04338961420308473 |

Both peaks are on the hole wall. At 2.5 mm, exclusion lowers the nodal peak by relative 0.026536677220455225 and does not change the integration-point peak. The kept nodal node is `(9.9436976651, 17.43731978, 0.0)` mm, also on the hole wall. At 1.25 mm, exclusion changes neither peak. Using the excluded nodal value on the coarser mesh would report a lower stress at the hole. That is enough to refuse the exclusion. The 1.25 mm minimum SICN is 0.04338961420308473. The last nodal step is relative +0.0333223293598294, which is smaller than the far-hole bracket's last step, on a mesh with a poor minimum SICN. No safety factor is emitted for this pair. The 10.665976946254995 factor does not apply to it.

#### Q11, fillet radius

A bracket with fillet radius 0 raises `GeometryError` `request_invalid` before meshing. The job status is `failed`, and `results/results.json` is not written. The only radius run through the three-size study is 3 mm. That study's stress samples did not flatten, so 3 mm is not a demonstrated minimum for stable stress. No smaller positive radius was solved. Thickness was not swept.

#### Bad models

The zero-fillet path is the test `test_zero_fillet_job_fails_without_a_safety_factor`.

The unrestrained model is one `C3D10` tetrahedron with 1 mm edges, a 1 N tip load, and no `*BOUNDARY`. On 2026-11-24 `ccx_static.exe` returned 0 and the parsed peak displacement was 117108275095.57127 mm. `require_bounded_displacement` raises `solver_failed` when the displacement is non-finite or greater than 10 times a characteristic length, here 10 mm. The deck does not contain `estimated_safety_factor`. The test `test_unrestrained_solid_fails_without_a_safety_factor` checks the exit code, the failure code, and the missing safety-factor text. It does not pin the displacement magnitude. That magnitude is from the run recorded here. The job directory is `artifacts/phase2/unrestrained`.

#### What Phase 2 does not claim

The safety factor is one unconverged nodal peak divided into a typical tensile yield that the cited sheet says is not for design. Displacement of the cantilever is close to Timoshenko beam theory. Bracket stress is not converged. Printed cards cannot be solved. Phase 3 is not approved. README status stays pre-MVP.

### Phase 3: Parametric optimization

**Goal:** Search thickness and fillet radius with the Phase 2 metric.

**Exit criteria:** A recorded search of at least three evaluations stores every iteration, selects the smallest feasible volume when one exists, and says the target was missed when none exist. Changing the mesh density does not silently change the winner without the result showing `mesh_converged`.

### Phase 4: FastAPI orchestration

**Goal:** Call the same runner over HTTP on localhost.

**In scope:** Pydantic models matching section 6, job status, artifact download, SQLite index, one-at-a-time execution, timeouts.

**Out of scope:** Accounts, multi-tenant isolation beyond separate job folders, and cloud deployment.

**Exit criteria:** An HTTP client can submit the beam or bracket request, poll until completion or failure, and download the STEP file and results JSON. Invalid directions and non-finite numbers never start `ccx`.

### Phase 5: React and Three.js visualization

**Goal:** Show the solid and the stored stress field.

**In scope:** Local web app, orbit controls, a color scale with units, the assumptions and disclaimer beside the number, and a before/after view only when two stored iterations exist.

**Exit criteria:** A person can run a local job from the UI and see a stress coloring that uses server-supplied nodal values. The page remains usable for a failed job by showing the failure code instead of a plot. Desktop layout is the target; a narrow viewport is checked so the disclaimer is not clipped away.

### Phase 6: Export workflows and user testing

**Goal:** Watch a small number of intended users, such as students, try the bracket flow.

**Exit criteria:** STEP and STL from a test job open in at least one external CAD or slicer tool. Notes from the sessions are recorded, including misunderstandings of the safety factor. No participant data is invented.

### Phase 7: Deployment and early customer validation

**Goal:** Decide whether any deployment is warranted.

**Exit criteria:** A machine size is chosen from measured solve time and memory. The license question Q10 is answered before distribution. Free-tier hosting is used only if a measured job fits its CPU, disk, and process limits. Otherwise the documented outcome may be "local-only."

## 10. Testing and Validation Strategy

Tests are added in the phase that creates the behavior. Phase 0 has no test suite. A test that is skipped because a solver is missing must say so. It must not be reported as a pass, and a mocked `ccx` must not be described as a structural validation.

### Unit tests

- Request ranges, hole edge heuristics, and direction-parallel checks
- Unit conversions, especially density from kg/m³ to tonne/mm³ and modulus from GPa to MPa
- Von Mises formula against hand-computed tensors, including pure uniaxial stress, where von Mises stress equals the absolute axial stress
- Safety-factor record when the metric is above and below the allowable stress
- Deck writer snapshots for a tiny hand-built mesh, so keyword drift is visible
- Failure mapping: timeout, missing file, and nonzero exit become `failed` and omit the safety factor

### Geometry tests

- Bounding box equals the requested envelope
- Volume is positive and stable across runs
- A known hole changes the volume by approximately the cylinder volume, within a kernel tolerance
- Fillet radius of zero is rejected for simulation
- An intersecting hole pair is rejected
- Face fingerprints exist for the mounting face, load face, and each hole cylinder
- STEP units are millimetres, checked by re-import or by file header inspection

### Mesh generation tests

- Imported bounding box agrees with CAD
- Each required role matches one unambiguous surface set on a fixture bracket, including a mounting face pierced by a hole
- A distorted fingerprint fixture fails closed
- Reportable meshes contain only 10-node tets
- Node-order fixture for one element
- Inverted elements fail the quality gate
- Element-count cap refuses a pathological size request before `ccx` starts

### Solver integration tests

- `ccx` is invoked on a small deck and returns the expected files
- A rigid-body case, with no restraint, is classified as failure
- The runner uses `shell=False` and a timeout
- Logs are stored on failure

These tests run only when the configured binary exists. The suite should report a clear skip reason otherwise.

### Analytical benchmark comparisons

Primary benchmark: slender rectangular cantilever.

- Axis along X, fixed on the face `x = 0`
- Transverse tip load P in the negative Z direction
- Section width `b`, depth `h`, length `L`, with `L / h` at least 10
- Second moment `I = b h^3 / 12`
- Euler-Bernoulli tip deflection `P L^3 / (3 E I)`
- Timoshenko addition for a rectangular section, using shear coefficient `6/5` and `G = E / (2 (1 + nu))`, so the shear term is `(6/5) P L / (A G)`
- Outer-fiber bending stress at the root `P L (h / 2) / I`

Compare displacement at a node that represents the tip, and compare bending stress only away from the fixed face and the loaded region. Expect a difference: the solid model's fixed face suppresses Poisson expansion, and a local load is not the beam theory's point load. Record the difference. Do not tune loads until the error disappears.

A later optional benchmark is an infinite-plate hole under far-field tension, where the elastic concentration factor is 3. That is not a Phase 1 gate. A bracket has no closed-form stress solution that should be pretended otherwise.

### Mesh refinement studies

For the beam and for one filleted bracket, solve at least three sizes, each substantially finer than the last. Tabulate element count, tip or maximum displacement, raw peak von Mises stress, and the candidate decision metric. Displacement should settle before the raw peak does. If the raw peak grows without bound at the fillet, the fillet is too sharp or the metric is sampling a singularity, and the decision metric must change.

No numerical tolerance is canonical until this table exists. A candidate band to try, not to treat as passed, is 5 percent on slender-beam tip displacement versus the Timoshenko value at the finest mesh. Stress bands will be wider and must be chosen from the table.

### Numerical tolerance checks

- Geometry match tolerances from section 7
- Bounding-box scale check before solve
- Von Mises unit-test tolerance at ordinary floating-point levels, around 1e-9 relative
- Benchmark comparisons use engineering tolerances from the refinement study, not the floating-point tolerance

### Regression tests

Once a beam solve has been accepted as a reference, store the expected displacement band and the input deck hash. Dependency upgrades of build123d, Gmsh, or `ccx` rerun this test. A move outside the band fails even if the solver exits cleanly.

Do not store a brittle snapshot of every nodal stress. Small mesher changes would make the suite noise. Guard integrated facts: node-count range, displacement band, and a couple of invariant checks.

### Physical validation strategy

Physical testing is not part of the automated suite and is not required to finish Phase 1.

A later, optional experiment for Phase 6 or Phase 7:

1. Print or machine one bracket whose geometry is a stored STEP file.
2. Record material, process, orientation, and actual dimensions.
3. Apply a load that resembles the modeled restraint and direction as closely as the fixture allows.
4. Measure deflection or the load at visible yield or fracture.
5. Compare only against the simulation assumptions. A disagreement can come from the restraint model, anisotropy, infill, or the test fixture. Write the disagreement down. Do not replace the solver result with the test result silently.

A printed specimen is not the homogeneous solid that was analyzed. Agreement does not certify the method. Disagreement does not by itself identify which assumption failed.

## 11. Known Technical Risks

| Risk | Why it matters | Planned response |
| --- | --- | --- |
| Unreliable face tagging | A load or restraint on the wrong face produces a tidy, meaningless result | Fingerprints, unique-match rule, fail closed, test with holes and fillet |
| Failed CAD booleans | Holes near edges and fillets defeat the kernel | Reject obvious intersections first. Treat kernel failures as `geometry_failed`. Keep the failing parameters in the log |
| Poor mesh quality | Inverted or coarse tets distort stiffness and stress | Jacobian gate, size relative to thickness, refinement study, element cap |
| Incorrect constraints | The fixed face is not a bolted joint, and a wrong `*DLOAD` face number applies pressure somewhere else | One restraint type, set-name allow-list, face-number check against the installed CalculiX manual, reaction balance, and a separate face-identity test |
| Stress concentrations and singularities | Peaks at the fillet, holes, restraints, and load patch can be mesh artifacts | Positive fillet, dual stress samples, refinement required before a decision metric, always store the raw peak |
| Solver convergence or singular failure | A missing restraint or a bad element aborts `ccx` | Structured failure, no safety factor, log retained |
| `C3D10` node-order mismatch | Stress and even displacement can be silently wrong | Single-element order check before interpreting the bracket |
| Anisotropic FDM behavior | Printed strength depends on layers and infill. The model is a solid isotropic continuum | Separate material basis, required limitation text, no implied print certification |
| Misleading safety factors | Linear stress past yield is not the plastic stress. A target safety factor sounds more certain than the model | `elastic_assumption_exceeded`, named metric, disclaimer copied into the result |
| Long or stuck solves | Fine tet meshes of a filleted part with holes can dominate a laptop | Element cap, timeout, local execution, no hosted free-tier assumption |
| Unit scaling | Millimetre geometry with pascal modulus, or Gmsh converting to metres, scales stress by 10³ or more | One unit system, bounding-box assertion, material range checks |
| GPL distribution | Shipping a closed-source app linked to Gmsh can violate the license chosen by Gmsh's authors | Local API allowed for development. Q10 required before proprietary distribution |
| Path spaces on Windows | The current profile path may break a scientific executable | Dedicated Phase 1 check, space-free artifact root if needed |
| Version skew | A future Gmsh or `ccx` build can change ordering, keywords, or FRD layout | Pin versions, parse only requested cards, keep the beam regression |

Successful `ccx` termination does not retire these risks.

## 12. Cursor Agent Operating Rules

Future agents working on this repository follow these rules.

1. Read `CONTEXT.md` before making architectural changes.
2. Read `README.md` to understand product goals and to avoid claiming features that are only planned.
3. Implement only the currently authorized phase. Phase 0 being complete does not authorize Phase 1. Wait for an explicit approval that names the phase.
4. Do not silently change technology choices. A replacement for build123d, Gmsh, CalculiX, the unit system, the storage plan, or the element type requires an update to the relevant ADR in this file first.
5. Keep geometry, meshing, simulation, and optimization logic in separate modules with files as the stage contract.
6. Document engineering assumptions explicitly in this file and in result records. New assumptions are labeled as assumptions until a test measures them.
7. Do not fabricate successful test results, timings, error percentages, or screenshots of runs that did not happen. If a solver is missing, say that the test was not run.
8. Run the relevant tests whenever the environment allows it. After a code change in a later phase, run the narrowest test that covers the change and any benchmark the change can affect.
9. Do not claim engineering certification, safety, code compliance, or experimental verification. Use "estimated," "simulated," and "under the stated assumptions."
10. Update `CONTEXT.md` after completing a development milestone: versions, measured benchmark numbers, newly closed questions, and the new phase status.
11. Record unresolved issues and the next step in this file rather than leaving them only in a chat.
12. Avoid unnecessary infrastructure and dependencies. Do not add MongoDB, Celery, Redis, Docker, FastAPI, or a frontend during Phase 1.
13. Use deterministic computation wherever practical. Pin versions, set mesh options explicitly, and record thread settings if results move between runs.
14. Never allow arbitrary untrusted Python or solver configuration to execute from user input. Requests stay inside the schemas in section 6.
15. Prefer reproducibility and correctness over impressive visual results. A stress color plot without a named metric and a mesh size is a defect.
16. Do not overwrite unrelated user files. Do not install into the global Python interpreter.
17. Do not mark a safety factor as available while `decision_metric` is still null in this document.
18. Keep the README status honest. It stays pre-MVP until the product acceptance list in section 4 is actually satisfied.

## 13. Next Actions

Phase 1 was approved on 2026-11-23 and the checklist below was carried out. Phase 2 was approved on 2026-11-24 and its checklist follows. Phase 3 is not approved. Do not start the search, the API, or the UI without a new approval.

1. Project virtual environment `.venv`, Python 3.12.6. Not the global interpreter.
2. Direct packages: build123d, Gmsh, NumPy, meshio, and pytest, pinned in `backend/requirements.lock`. FastAPI, React, and a database were not added. SciPy and scikit-learn are present only because build123d depends on them. LoadCAD does not import them.
3. CalculiX 2.22 `ccx_static.exe` recorded in section 9. Q1 is answered.
4. Path-space probe recorded. Q9 is answered for that probe.
5. Cantilever constructor and Euler-Bernoulli / Timoshenko formulas, with unit tests.
6. `C3D10` solve. Q4 is answered: use `swap_last_two`, not raw Gmsh order.
7. FRD displacement, stress, and `FORC` reactions parsed. Von Mises stored. Safety factor omitted.
8. Displacement error for the single 5 mm mesh recorded. No tolerance band.
9. Filleted L-bracket fixture with two holes.
10. STEP and STL in millimetres. Import bounding box checked. Q2 is answered for these solids.
11. `mounting_outer` and `horizontal_top` matched as disjoint tag sets on the fixture. Q3 is answered for that fixture only.
12. Bracket solved. Fixed-face reaction residual recorded in section 9. Balance is not treated as proof of face identity.
13. Job directories written under `artifacts/phase1/beam` and `artifacts/phase1/bracket`.
14. This file and `README.md` updated from those runs.
15. Stop.

Phase 2 checklist, carried out on 2026-11-24:

1. Versioned cards for `aluminum_6061_t6`, `prusament_pla`, and `prusament_petg`. Q8 is answered. Printed cards fail `require_solvable()`.
2. Integration-point stress is read from `*EL PRINT` with the DAT component order corrected before von Mises.
3. Bracket pressure uses the quadratic face area. Corner area is still stored.
4. Beam and bracket refinements at 5, 2.5, and 1.25 mm. Tables are in `backend/studies/` and section 9.
5. Q5 is answered for displacement. No stress band is declared.
6. Q6: `decision_metric` is `max_nodal_von_mises`. Exclusion was not adopted.
7. Q7: no stress convergence band. `mesh_converged` is false.
8. The aluminum bracket safety-factor record includes every field in section 5. The value is 10.665976946254995 with the disclaimer and `elastic_assumption_exceeded` false.
9. Q12 was checked with a horizontal hole at the 10.5 mm clearance. Exclusion was slightly unconservative at 2.5 mm and neutral at 1.25 mm.
10. A zero fillet fails as `request_invalid` with no results file. An unrestrained tet exits 0 and is then classified `solver_failed` with no safety factor.
11. This file and `README.md` updated from those runs.
12. Stop. Do not start Phase 3.

Remaining gaps, none of which authorize Phase 3 by themselves:

- Bracket stress is still rising. `STRESS_RELATIVE_BAND` is unset on purpose.
- The 1.25 mm aluminum bracket reaction is still short by 0.01222320739569227 N.
- Q11 has no minimum fillet for stable stress. Only radius 0 and radius 3 mm were exercised, and radius 3 mm did not converge.
- Q10, the project license and the Gmsh distribution question, is still open.
- PLA and PETG cannot be solved until a Poisson ratio for those products is cited.
- The near-hole 1.25 mm mesh has minimum SICN 0.04338961420308473. No quality threshold rejected it.
- `cadgmsh` was not tried. Direct STEP import remains the path that was run.

## Source notes from Phase 0

Checked on 2026-11-22 from public documentation and the local machine. These notes justify the plan. They are not benchmark results.

- build123d is Apache-2.0 and exports STEP in a chosen unit, defaulting to millimetres, and STL as a unitless triangle file. Face labels on a constructed solid are not a reliable identity across `faces()` or STEP `ADVANCED_FACE` entities.
- Gmsh 4.15.2 is GPL-2.0-or-later. The official manual documents `pip install gmsh`, Open CASCADE import, and physical groups. If physical groups exist, exporters usually write only grouped entities.
- CalculiX is GPL-2.0. The 2.21 manual describes `C3D10`, unitless input, nodal FRD output, and more accurate element quantities at integration points. Project discussion with the CalculiX author states that von Mises stress is computed by the post-processor from stress components.
- conda-forge has published a Windows CalculiX 2.22 package. A discourse thread on 2025-09-23 pointed Windows users at a `dhondt.de` zip. Phase 0 had not downloaded either one. Phase 1 downloaded the `dhondt.de` zip named in section 9 and ran `ccx_static.exe`. The conda-forge package was not used.
- meshio is MIT and lists Gmsh and Abaqus inputs among its formats. `.frd` was not in that list.
- `cadgmsh` 0.4.0 exists, is MIT, and is not adopted.
- Local commands showed Python 3.12.6 and Git 2.45.1, and did not find `ccx`, `gmsh`, or conda on `PATH`.

Where this file gives a tolerance, a size cap, an edge-distance heuristic, or a material number without a measurement or a citation, it is a hypothesis for the next phase, not a result.
