# LoadCAD

**Describe what a part needs to withstand. LoadCAD designs and simulates it.**

**Status: pre-MVP. Phase 0, documentation only.**

LoadCAD has no application code yet. It has not generated a part, meshed a solid, or run a finite-element analysis. Nothing in this repository is a simulation result, a certified design, or a measured performance claim.

The engineering source of truth for contributors and future coding sessions is [CONTEXT.md](CONTEXT.md). This README explains the product and the planned architecture. Where the two files disagree, `CONTEXT.md` wins until both are updated together.

## Overview

LoadCAD is an early-stage mechanical design and structural simulation platform. The long-term aim is to turn a physical requirement into a parametric, manufacturable design candidate and a transparent structural simulation.

The first product is deliberately narrow: a parametric L-shaped mounting bracket. A user will describe the envelope, wall thickness, bolt holes, material, applied force, and target safety factor. The planned pipeline generates the solid, meshes it, runs a linear-elastic static analysis, estimates a safety factor under stated assumptions, and exports CAD files.

The design is produced by explicit parametric geometry and a numerical solver. A language model may help write the software. It does not invent the solid, the mesh, or the stress field.

## The problem

Designing even a simple bracket still requires several specialized tools and judgments:

1. Model the solid in CAD.
2. Choose how it is held and how the load is applied.
3. Build a finite-element mesh.
4. Assign a material and run a solver.
5. Interpret stresses that may be misleading at corners, holes, and load points.
6. Change the geometry and repeat.

Students, robotics teams, and small hardware groups can do this, but the handoff between CAD, meshing, and analysis is slow and easy to get wrong. A model that solves is not automatically a model that means anything physically.

## Proposed solution

LoadCAD will own that handoff for one part family.

```text
Design requirements
        |
        v
Input validation
        |
        v
Parametric geometry
        |
        v
Geometry validation
        |
        v
Mesh generation
        |
        v
Material and boundary conditions
        |
        v
Linear static finite-element analysis
        |
        v
Result extraction and constraint checks
        |
        v
Bounded parameter changes, then repeat when needed
        |
        v
3D view and downloadable artifacts
```

Each stage will write files into a job folder. The next stage reads those files. A successful solver exit code will be stored as a job fact, not as proof that the bracket is adequate.

The planned safety factor is a post-processing estimate:

`estimated safety factor = allowable stress / selected von Mises stress metric`

The allowable stress, the stress metric, the mesh size, and the restraint model will be stored with the result. Linear elasticity stops being a physical stress prediction once the computed stress passes yield. A result in that range will be labeled as an exceeded modeling assumption.

## Target users

Initial audience:

- Robotics students and competition teams
- Mechanical engineering students
- 3D-printing enthusiasts
- Makers and hardware hackers
- University engineering laboratories
- Small hardware startups

Possible later customers, after the pipeline is validated and the product is actually deployed:

- Mechanical engineering teams
- Product design studios
- Rapid-prototyping shops
- Manufacturing workshops
- Industrial design organizations

There are no customers, users, or usage figures yet.

## MVP features

The product MVP is one component family: **parametric L-brackets**. These features are planned. None are implemented.

| Planned capability | What the user provides or receives |
| --- | --- |
| Bracket envelope | Width, height, length, and a common wall thickness |
| Inside fillet | Fillet radius. Required for any run that reports stress |
| Bolt holes | A short list of through-holes on the vertical leg, the horizontal leg, or both |
| Material | A named isotropic linear-elastic card with a cited allowable stress |
| Load | One static force magnitude and direction on one supported face |
| Target | A safety-factor target used as a design constraint |
| Geometry output | STEP and STL, in millimetres |
| Analysis | Tetrahedral mesh, CalculiX linear static solve, displacement and stress extraction |
| Design loop | Change supported dimensions and keep every iteration |
| Review | On-screen geometry and stress coloring, plus downloadable artifacts |

The first supported structural case is narrower than the schema:

- The outer vertical face is fully fixed.
- The force is normal to the top of the horizontal leg.
- Bolts, contact, preload, friction, and gravity are not modeled.

Arbitrary force directions remain in the data model and will be rejected by validation until a traction method has been checked against a known solution.

## Intended user experience

This flow is the intended product behavior after the later implementation phases. It cannot be exercised today.

1. Select an L-bracket.
2. Enter dimensions, holes, material, force, and target safety factor.
3. Correct any constraint errors before a job starts.
4. Submit the job and follow its status: geometry, mesh, solve, post-processing.
5. Inspect the solid and a stress coloring, with the modeling assumptions visible.
6. Read the estimated safety factor, including whether the elastic model was exceeded.
7. Download STEP, STL, and a results summary that points back to the solver files.
8. Change thickness or fillet radius and compare the stored iterations.

A failed mesh or a failed solve ends as a failed job. It does not return a safety factor.

## Planned system architecture

LoadCAD will be a local pipeline first and a web application only after that pipeline reproduces an analytical beam result.

| Module | Responsibility | Contract with the next module |
| --- | --- | --- |
| Request validation | Accept numbers and enumerations. Reject paths, scripts, and raw solver text | Validated request record |
| Geometry | Build the bracket in build123d and record a fingerprint for every semantic face | STEP, STL, face-map file |
| Meshing | Import the solid in Gmsh, match faces by geometry, build physical groups, mesh | Mesh plus node sets |
| Solver input | Write a CalculiX deck from those sets. Apply the material card and restraints | `.inp` file |
| Solver execution | Run unmodified `ccx` as a separate process with a timeout | `.frd`, `.dat`, and the log |
| Post-processing | Compute von Mises stress and the safety-factor estimate from solver output | Results record |
| Search | Vary only allow-listed dimensions and repeat the pipeline | Iteration records |
| Delivery | Serve status, previews, and file downloads | API and web UI, later |

Phases 1 through 3 call these modules as Python functions and pass a job directory between them. HTTP, a database, and the browser UI come after the numerical path is testable.

Storage for the MVP is the job directory. SQLite is the planned index once an API needs queries. MongoDB is not part of the MVP. A task broker such as Celery is not part of the MVP. One local solver process is enough until concurrent jobs are a demonstrated requirement.

## Technology stack

The stack below was reviewed during Phase 0. "Selected" means selected for the plan, not installed for this project.

| Area | Choice | Phase 0 decision |
| --- | --- | --- |
| Language | Python 3.11 or newer. This machine has Python 3.12.6 | Selected for the numerical pipeline |
| CAD | build123d on Open CASCADE | Selected. Apache-2.0 library, Open CASCADE under LGPL-2.1 with the OCCT exception |
| Meshing | Gmsh 4.x through its Python API | Selected for local development. GPL-2.0-or-later; see License |
| FEA | CalculiX CrunchiX (`ccx`), linear static analysis | Selected. GPL-2.0. Not installed on this machine |
| Mesh helper | meshio and NumPy | Selected. The CalculiX deck and the result reader are project code; meshio does not replace them |
| Optimization numerics | Plain deterministic parameter search first | SciPy is deferred until a search actually needs it |
| API | FastAPI and Pydantic | Deferred to Phase 4 |
| UI | React, TypeScript, Vite, Three.js, React Three Fiber, Tailwind CSS | Deferred to Phase 5 |
| Job index | Files, then SQLite | MongoDB rejected for the MVP |
| Queue | A subprocess with a timeout | Celery rejected until concurrency requires it |
| Deployment | The developer machine | Docker is a later reproducibility aid. Free hosting tiers are not a plan for running analysis |

build123d, Gmsh, and CalculiX are a practical combination because they meet through files and open geometry kernels: STEP or BREP into Gmsh's Open CASCADE kernel, then nodes and elements into a CalculiX input deck. Face names do not reliably survive that path. The bracket generator will record geometric fingerprints and rematch faces after import. That match is a design requirement, and it has not been tested.

`ccx` is not available as a normal Python package. Phase 1 has to obtain a Windows CalculiX 2.22 binary and record the exact build before any bracket result is interpreted. Candidate sources are listed in `CONTEXT.md`. None of them has been downloaded or run by this project.

## Engineering and simulation limitations

Every future result screen and report needs to stay compatible with the following limits.

- The analysis is linear, static, isotropic, and small-displacement. It is not a nonlinear, dynamic, fatigue, buckling, or contact analysis.
- Fixing the entire mounting face is stiffer and different from a bolted joint.
- A force applied as pressure is supported only when it is normal to the loaded face.
- Ten-node tetrahedra (`C3D10`) are the planned element. Linear tetrahedra are a known poor default for this kind of stress result and are not the decision model.
- Re-entrant corners without a fillet make the elastic stress unbounded as the mesh is refined. Simulation jobs require a positive fillet radius.
- Peak stress at a restraint, a load, or a hole can be a numerical singularity. The reported metric has to be defined and compared across mesh sizes.
- CalculiX writes stress components. LoadCAD will compute von Mises stress during post-processing. Averaged nodal values and integration-point values are different quantities; the result must name which one it used.
- Filament materials such as PLA and PETG are anisotropic and process-dependent when printed. An isotropic card is an approximation, not a description of a printed part.
- A safety factor from this model is not a certification, a guarantee of safety, or a substitute for physical testing.
- A completed solver run only proves that this particular numerical problem returned a solution.

## Project status

| Item | State |
| --- | --- |
| Phase | 0, documentation and planning |
| Application source | None |
| Dependencies installed for LoadCAD | None. No project environment or lockfile |
| CAD, mesh, or FEA runs performed by LoadCAD | None |
| Tests | None |
| Hosted service | None |
| License | Not selected |

Observed on the development machine during Phase 0: Windows, Python 3.12.6, Git 2.45.1, and a repository on `main` with no commits before these documents. `ccx` and `gmsh` were not on `PATH`. `build123d` was not importable. NumPy, SciPy, FastAPI, and Pydantic happened to be importable from the system interpreter. That does not create a project environment, and Phase 1 should not install into that global interpreter.

## Development roadmap

| Phase | Goal | Starts only when |
| --- | --- | --- |
| 0 | README and context | Complete with this document |
| 1 | Headless CAD, Gmsh, and CalculiX proof, including a beam benchmark | Explicit approval |
| 2 | Material cards, restraints, result metrics, and mesh-refinement checks | Phase 1 exit criteria are met and recorded |
| 3 | Bounded search over thickness and fillet radius | A defined stress metric exists |
| 4 | FastAPI job orchestration and a SQLite index | The headless pipeline can be called as a function |
| 5 | React and Three.js geometry and stress view | The API can return a completed job and its artifacts |
| 6 | Export polish and supervised user testing | A person can run the local product flow |
| 7 | Deployment and early customer validation | A local benchmark and a chosen license exist |

Phases are sequential on purpose. A web interface before a verified solver path would display untrusted numbers.

## Planned local development requirements

No install commands are listed here because the project does not have code, a dependency manifest, or a tested solver command yet.

Phase 1 will need:

- Python 3.11 or newer, with a project-local virtual environment
- build123d and the Gmsh Python package
- An unmodified CalculiX `ccx` executable, pinned to a recorded version and path
- Git
- Enough local disk for mesh and result files
- A job directory whose solver working path has been tested on this machine. The current user profile path contains a space, which some scientific tools handle poorly

Docker, a database server, Redis, and a cloud account are not required to begin Phase 1.

## Zero-cost development philosophy

Initial development stays on free and open-source tools, run locally:

- Open-source geometry, meshing, and finite-element software
- The developer workstation as the only compute resource
- Ordinary files as the system of record, with SQLite only when queries are needed
- No paid solver and no cloud analysis queue
- No hosted database tier used as a substitute for a solver

Free application-hosting tiers are a poor fit for finite-element work. They are often small, short-lived, or asleep, and a free database tier does not supply the CPU or the working disk a mesh solve needs. Hosting decisions wait until the local pipeline is proven and a real deployment requirement exists.

## Future vision

After the L-bracket path is both numerically and physically scrutinized, the same architecture can grow toward more part families, load cases, materials, and manufacturing processes. Candidates for that later work include more bracket topologies, multiple load cases, orthotropic print models, richer manufacturing checks, and collaborative project history.

Those additions are out of scope until the single-bracket pipeline is measurable. The platform should get wider by adding verified part families, not by generating arbitrary solids from text.

## Contributing

External contributions are not open yet. The license and contribution terms are unset.

Anyone working in this repository, including an automated coding agent, should:

1. Read [CONTEXT.md](CONTEXT.md) before changing architecture or dependencies.
2. Stay inside the implementation phase that has been explicitly approved.
3. Keep geometry, meshing, solving, and optimization as separate modules.
4. Record assumptions, failed runs, and tool versions.
5. Avoid presenting an unrun or failed analysis as a successful result.

## License

No project license has been chosen. Until a `LICENSE` file is added, all rights in the project documents and any future project code are reserved by the copyright holder.

The planned third-party tools have their own obligations:

- build123d is Apache-2.0.
- Open CASCADE, used through build123d's bindings, is LGPL-2.1 with the Open CASCADE exception.
- Gmsh is GPL-2.0-or-later. Importing it into a distributed closed-source application can create a licensing conflict. A commercial Gmsh license exists for parties who need one.
- CalculiX is GPL-2.0.
- meshio is MIT.

Running an unmodified GPL program as a separate process is the planned engineering boundary. It is not a legal opinion. The project license and the Gmsh distribution choice must both be settled before LoadCAD is shipped as a proprietary product.

## Further reading

[CONTEXT.md](CONTEXT.md) contains the unit system, coordinate conventions, data models, solver pipeline, architecture decisions, test strategy, risks, and the Phase 1 checklist.
