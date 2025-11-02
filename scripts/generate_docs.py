#!/usr/bin/env python3
"""
OpenSpec Documentation Generator
Generates comprehensive documentation from OpenSpec definitions.
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, List
import argparse

class OpenSpecDocGenerator:
    """Generate documentation from OpenSpec definitions"""

    def __init__(self):
        self.specs: Dict[str, Dict[str, Any]] = {}

    def load_specs(self, spec_dir: Path) -> None:
        """Load all OpenSpec specifications"""
        for spec_file in spec_dir.glob("openspec_*.md"):
            self._parse_spec_file(spec_file)

    def _parse_spec_file(self, file_path: Path) -> None:
        """Parse OpenSpec markdown file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        spec_blocks = re.findall(r'```openspec\s*(.*?)\s*```', content, re.DOTALL)

        for block in spec_blocks:
            try:
                spec_data = yaml.safe_load(block.strip())
                if spec_data and 'component' in spec_data:
                    self.specs[spec_data['component']] = spec_data
            except yaml.YAMLError as e:
                print(f"Warning: Failed to parse spec in {file_path}: {e}")

    def generate_component_docs(self) -> str:
        """Generate component documentation"""
        lines = [
            '# OpenSpec Component Reference\n',
            'This document provides detailed specifications for all OpenSpec components.\n',
            '## Components\n'
        ]

        for component_name, spec in sorted(self.specs.items()):
            lines.extend(self._generate_component_section(component_name, spec))

        return '\n'.join(lines)

    def _generate_component_section(self, name: str, spec: Dict[str, Any]) -> List[str]:
        """Generate documentation section for a component"""
        lines = [
            f'### {name}\n',
            f'**Version**: {spec.get("version", "1.0.0")}\n',
        ]

        if 'interface' in spec:
            lines.extend([
                '**Interface**:\n',
                '```python',
                spec['interface'],
                '```\n',
            ])

        if 'implementations' in spec:
            lines.extend([
                '**Implementations**:\n',
            ])
            for impl in spec['implementations']:
                lines.append(f'- {impl}')
            lines.append('')

        if 'validation' in spec:
            lines.extend([
                '**Validation Rules**:\n',
            ])
            for rule in spec['validation']:
                lines.append(f'- {rule}')
            lines.append('')

        if 'providers' in spec:
            lines.extend([
                '**Supported Providers**:\n',
            ])
            for provider in spec['providers']:
                lines.append(f'- {provider}')
            lines.append('')

        if 'quality_options' in spec:
            lines.extend([
                '**Quality Options**:\n',
            ])
            for option in spec['quality_options']:
                lines.append(f'- {option}')
            lines.append('')

        if 'platforms' in spec:
            lines.extend([
                '**Supported Platforms**:\n',
            ])
            for platform in spec['platforms']:
                lines.append(f'- {platform}')
            lines.append('')

        return lines

    def generate_integration_guide(self) -> str:
        """Generate integration guide"""
        lines = [
            '# OpenSpec Integration Guide\n',
            'This guide explains how to integrate OpenSpec components into your application.\n',
            '## Pipeline Configuration\n',
            'Components are configured through the pipeline configuration system:\n',
            '```python',
            'PIPELINE_COMPONENTS = {',
            '    "script_provider": "gemini",',
            '    "voice_pipeline": "tts",',
            '    "editing_backend": "moviepy",',
            '    "platform_adapter": "youtube"',
            '}',
            '```\n',
            '## Component Injection\n',
            'Components are automatically injected based on configuration:\n',
            '```python',
            'from src.core.pipeline import build_default_pipeline',
            '',
            'pipeline = await build_default_pipeline()',
            'result = await pipeline.run(topic="Your Topic")',
            '```\n',
            '## Custom Implementations\n',
            'To add custom implementations:\n',
            '1. Implement the required interface',
            '2. Add to OpenSpec specification',
            '3. Register in pipeline configuration\n',
            '## Validation\n',
            'Run validation to ensure compliance:\n',
            '```bash',
            'python scripts/validate_openspec.py',
            '```\n'
        ]

        return '\n'.join(lines)

    def generate_api_reference(self) -> str:
        """Generate API reference"""
        lines = [
            '# OpenSpec API Reference\n',
            'Complete API reference for OpenSpec components.\n',
            '## Core Interfaces\n'
        ]

        for component_name in sorted(self.specs.keys()):
            lines.extend([
                f'### {component_name}\n',
                f'Detailed API for {component_name}.\n',
                '#### Methods\n',
                '- See interface definition for method signatures\n',
                '#### Error Handling\n',
                '- Implementations should raise appropriate exceptions\n',
                '#### Async Support\n',
                '- All methods are async for non-blocking operations\n',
            ])

        return '\n'.join(lines)

def main():
    """Main documentation generator"""
    parser = argparse.ArgumentParser(description='Generate documentation from OpenSpec definitions')
    parser.add_argument('--spec-dir', default='docs', help='Directory containing OpenSpec files')
    parser.add_argument('--output-dir', default='docs/generated', help='Output directory for generated docs')

    args = parser.parse_args()

    spec_dir = Path(args.spec_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = OpenSpecDocGenerator()
    generator.load_specs(spec_dir)

    print(f"Loaded {len(generator.specs)} component specifications")

    # Generate component reference
    component_docs = generator.generate_component_docs()
    with open(output_dir / 'openspec_components_ref.md', 'w', encoding='utf-8') as f:
        f.write(component_docs)

    # Generate integration guide
    integration_guide = generator.generate_integration_guide()
    with open(output_dir / 'openspec_integration.md', 'w', encoding='utf-8') as f:
        f.write(integration_guide)

    # Generate API reference
    api_ref = generator.generate_api_reference()
    with open(output_dir / 'openspec_api_ref.md', 'w', encoding='utf-8') as f:
        f.write(api_ref)

    print(f"Generated documentation in {output_dir}")
    return 0

if __name__ == "__main__":
    exit(main())
