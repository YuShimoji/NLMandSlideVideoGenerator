#!/usr/bin/env python3
"""Test OpenSpec documentation generation"""

from pathlib import Path
from scripts.generate_docs import OpenSpecDocGenerator

def main():
    # Create generator
    generator = OpenSpecDocGenerator()

    # Load specs
    spec_dir = Path("docs")
    generator.load_specs(spec_dir)

    print(f"Loaded {len(generator.specs)} specs: {list(generator.specs.keys())}")

    # Generate documentation
    component_docs = generator.generate_component_docs()
    integration_guide = generator.generate_integration_guide()
    api_ref = generator.generate_api_reference()

    # Write files
    output_dir = Path("docs/generated")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "openspec_components_ref.md", 'w', encoding='utf-8') as f:
        f.write(component_docs)

    with open(output_dir / "openspec_integration.md", 'w', encoding='utf-8') as f:
        f.write(integration_guide)

    with open(output_dir / "openspec_api_ref.md", 'w', encoding='utf-8') as f:
        f.write(api_ref)

    print("Documentation generated successfully!")

if __name__ == "__main__":
    main()
