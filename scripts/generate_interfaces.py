#!/usr/bin/env python3
"""
OpenSpec Interface Generator
Generates Python interface stubs from OpenSpec definitions.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import argparse

class OpenSpecInterfaceGenerator:
    """Generate Python interfaces from OpenSpec definitions"""

    def __init__(self):
        self.type_mapping = {
            'str': 'str',
            'int': 'int',
            'float': 'float',
            'bool': 'bool',
            'Dict[str, Any]': 'Dict[str, Any]',
            'List[SourceInfo]': 'List[SourceInfo]',
            'Optional[str]': 'Optional[str]',
            'Optional[datetime]': 'Optional[datetime]',
            'AudioInfo': 'AudioInfo',
            'VideoInfo': 'VideoInfo',
            'SlidesPackage': 'SlidesPackage',
            'TranscriptInfo': 'TranscriptInfo',
            'UploadResult': 'UploadResult',
            'UploadMetadata': 'UploadMetadata',
        }

    def parse_spec_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse OpenSpec definitions from markdown file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract code blocks with openspec language
        spec_blocks = re.findall(r'```openspec\s*(.*?)\s*```', content, re.DOTALL)

        specs = []
        for block in spec_blocks:
            try:
                spec_data = yaml.safe_load(block.strip())
                if spec_data and 'component' in spec_data:
                    specs.append(spec_data)
            except yaml.YAMLError as e:
                print(f"Warning: Failed to parse spec block: {e}")

        return specs

    def generate_interface(self, spec: Dict[str, Any]) -> str:
        """Generate Python interface code from spec"""
        component_name = spec['component']
        interface_def = spec.get('interface', '')

        # Parse interface methods
        methods = self._parse_interface_methods(interface_def)

        # Generate class definition
        code_lines = [
            '"""',
            f'OpenSpec Interface: {component_name}',
            f'Generated from OpenSpec definition v{spec.get("version", "1.0.0")}',
            '"""',
            'from __future__ import annotations',
            '',
            'from typing import Protocol, List, Optional, Union, Dict, Any',
            'from abc import ABC, abstractmethod',
            '',
            '# Import required types',
            'from notebook_lm.source_collector import SourceInfo',
            'from notebook_lm.audio_generator import AudioInfo',
            'from notebook_lm.transcript_processor import TranscriptInfo',
            'from slides.slide_generator import SlidesPackage',
            'from video_editor.video_composer import VideoInfo',
            'from youtube.uploader import UploadResult, UploadMetadata',
            'from datetime import datetime',
            '',
            '',
            f'class {component_name}(Protocol):',
            f'    """OpenSpec Protocol for {component_name}"""',
            '',
        ]

        for method_name, method_info in methods.items():
            code_lines.extend([
                f'    @abstractmethod',
                f'    async def {method_name}(',
            ])

            # Add parameters
            params = method_info['params']
            if params:
                for i, param in enumerate(params):
                    prefix = '        ' if i == 0 else '              '
                    comma = ',' if i < len(params) - 1 else ''
                    code_lines.append(f'{prefix}{param}{comma}')

            # Add return type
            return_type = method_info.get('return_type', 'None')
            code_lines.extend([
                f'    ) -> {return_type}:',
                f'        """{method_info.get("doc", f"Abstract method {method_name}")}"""',
                '        ...',
                '',
            ])

        # Add implementation list as comment
        if 'implementations' in spec:
            code_lines.extend([
                '    # Known implementations:',
            ])
            for impl in spec['implementations']:
                code_lines.append(f'    # - {impl}')

        return '\n'.join(code_lines)

    def _parse_interface_methods(self, interface_str: str) -> Dict[str, Dict[str, Any]]:
        """Parse method signatures from interface string"""
        methods = {}

        # Split by method definitions (async def)
        method_pattern = r'async def (\w+)\s*\(([^)]*)\)\s*->\s*([^:\n]+)'
        matches = re.findall(method_pattern, interface_str)

        for method_name, params_str, return_type in matches:
            # Parse parameters
            params = []
            if params_str.strip():
                param_list = [p.strip() for p in params_str.split(',')]
                for param in param_list:
                    if ':' in param:
                        param_name, param_type = param.split(':', 1)
                        params.append(f'{param_name.strip()}: {param_type.strip()}')
                    else:
                        params.append(param.strip())

            methods[method_name] = {
                'params': params,
                'return_type': return_type.strip(),
                'doc': f'Abstract method {method_name} from OpenSpec interface'
            }

        return methods

def main():
    """Main generator function"""
    parser = argparse.ArgumentParser(description='Generate Python interfaces from OpenSpec definitions')
    parser.add_argument('--spec', required=True, help='OpenSpec markdown file')
    parser.add_argument('--output', required=True, help='Output directory for generated interfaces')
    parser.add_argument('--component', help='Specific component to generate (optional)')

    args = parser.parse_args()

    spec_file = Path(args.spec)
    output_dir = Path(args.output)

    if not spec_file.exists():
        print(f"Error: Spec file not found: {spec_file}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    generator = OpenSpecInterfaceGenerator()
    specs = generator.parse_spec_file(spec_file)

    generated_count = 0

    for spec in specs:
        component_name = spec['component']

        if args.component and component_name != args.component:
            continue

        interface_code = generator.generate_interface(spec)

        output_file = output_dir / f'{component_name.lower()}.py'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(interface_code)

        print(f"Generated interface: {output_file}")
        generated_count += 1

    print(f"\nGenerated {generated_count} interface files")
    return 0

if __name__ == "__main__":
    exit(main())
