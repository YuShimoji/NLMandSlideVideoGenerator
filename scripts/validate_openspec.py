#!/usr/bin/env python3
"""
OpenSpec Validation Tool for NLMandSlideVideoGenerator
Validates component implementations against OpenSpec definitions.
"""

import json
import yaml
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import importlib
import inspect

class OpenSpecValidator:
    """OpenSpec component validator"""

    def __init__(self, spec_dir: Path):
        self.spec_dir = spec_dir
        self.specs: Dict[str, Dict[str, Any]] = {}

    def load_specs(self) -> None:
        """Load all OpenSpec definition files"""
        for spec_file in self.spec_dir.glob("*.md"):
            if spec_file.name.startswith("openspec_"):
                self._parse_spec_file(spec_file)

    def _parse_spec_file(self, file_path: Path) -> None:
        """Parse OpenSpec markdown file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract code blocks with openspec language
        import re
        spec_blocks = re.findall(r'```openspec\s*(.*?)\s*```', content, re.DOTALL)

        for block in spec_blocks:
            try:
                # Parse YAML-like structure
                spec_data = yaml.safe_load(block.strip())
                if spec_data and 'component' in spec_data:
                    self.specs[spec_data['component']] = spec_data
            except yaml.YAMLError as e:
                print(f"Warning: Failed to parse spec block in {file_path}: {e}")

    def validate_component(self, component_name: str, implementation_class: Any) -> List[str]:
        """Validate component implementation against spec"""
        if component_name not in self.specs:
            return [f"No spec found for component: {component_name}"]

        spec = self.specs[component_name]
        errors = []

        # Check interface methods
        if 'interface' in spec:
            interface_methods = self._extract_interface_methods(spec['interface'])
            implementation_methods = self._get_class_methods(implementation_class)

            for method_name, method_sig in interface_methods.items():
                if method_name not in implementation_methods:
                    errors.append(f"Missing method: {method_name}")
                else:
                    # Could add signature validation here
                    pass

        # Check implementations
        if 'implementations' in spec:
            if implementation_class.__name__ not in spec['implementations']:
                errors.append(f"Implementation {implementation_class.__name__} not in allowed list: {spec['implementations']}")

        return errors

    def _extract_interface_methods(self, interface_str: str) -> Dict[str, str]:
        """Extract method signatures from interface string"""
        methods = {}
        lines = interface_str.strip().split('\n')
        for line in lines:
            line = line.strip()
            if '(' in line and ')' in line:
                method_match = re.match(r'(\w+)\s*\([^)]*\)', line)
                if method_match:
                    methods[method_match.group(1)] = line
        return methods

    def _get_class_methods(self, cls: Any) -> Dict[str, Any]:
        """Get all methods of a class"""
        return {name: method for name, method in inspect.getmembers(cls, predicate=inspect.isfunction)
                if not name.startswith('_')}

def main():
    """Main validation function"""
    project_root = Path(__file__).parent.parent
    spec_dir = project_root / "docs"

    validator = OpenSpecValidator(spec_dir)
    validator.load_specs()

    print(f"Loaded {len(validator.specs)} component specifications")

    # Validate core components
    components_to_validate = [
        ("IScriptProvider", "src.core.providers.script.gemini_provider", "GeminiScriptProvider"),
        ("IVoicePipeline", "src.core.voice_pipelines.tts_voice_pipeline", "TTSVoicePipeline"),
        ("IEditingBackend", "src.core.editing.moviepy_backend", "MoviePyEditingBackend"),
        ("IEditingBackend", "src.core.editing.ymm4_backend", "YMM4EditingBackend"),
        ("IPlatformAdapter", "src.core.platforms.youtube_adapter", "YouTubePlatformAdapter"),
    ]

    all_errors = []

    for interface_name, module_path, class_name in components_to_validate:
        try:
            module = importlib.import_module(module_path.replace('/', '.'))
            cls = getattr(module, class_name)
            errors = validator.validate_component(interface_name, cls)

            if errors:
                print(f"❌ {class_name}: {len(errors)} validation errors")
                for error in errors:
                    print(f"  - {error}")
                all_errors.extend(errors)
            else:
                print(f"✅ {class_name}: Validation passed")

        except ImportError as e:
            print(f"❌ {class_name}: Import failed - {e}")
            all_errors.append(f"Import failed for {class_name}")
        except AttributeError as e:
            print(f"❌ {class_name}: Class not found - {e}")
            all_errors.append(f"Class not found: {class_name}")

    if all_errors:
        print(f"\n❌ Validation failed with {len(all_errors)} total errors")
        sys.exit(1)
    else:
        print("\n✅ All component validations passed!")

if __name__ == "__main__":
    main()
