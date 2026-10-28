// swift-tools-version: 5.9
//
// Only the Core layer is declared here. The UI layer under `Jarvaids/UI/` is owned by
// a different workstream, so it adds its own target rather than having one declared
// for it against files that may not exist yet.

import PackageDescription

let package = Package(
    name: "Jarvaids",
    // Observation's `@Observable` macro and `Duration`-based `Task.sleep(for:)` set
    // the floor. Nothing here needs anything newer.
    platforms: [
        .iOS(.v17),
        .macOS(.v14),
    ],
    products: [
        .library(name: "JarvaidsCore", targets: ["JarvaidsCore"]),
    ],
    // No dependencies, deliberately. The backend contract is plain JSON over HTTP and
    // the standard library plus Foundation cover all of it. See README.md.
    dependencies: [],
    targets: [
        .target(
            name: "JarvaidsCore",
            path: "Jarvaids/Core",
            swiftSettings: [
                // Surfaces data-race problems now rather than at the Swift 6 migration.
                .enableExperimentalFeature("StrictConcurrency")
            ]
        ),
    ]
)
