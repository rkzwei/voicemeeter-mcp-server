"""
Enhanced Preset Management System for Voicemeeter MCP Server

This module provides advanced preset management capabilities including:
- JSON schema validation for preset files
- Preset comparison and diff functionality
- Automatic backup and versioning
- Preset template system
- Error handling and recovery
"""

import hashlib
import json
import logging
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from xml.etree.ElementTree import Element, ElementTree, SubElement, indent

import defusedxml.ElementTree as ET
import jsonschema

logger = logging.getLogger(__name__)


@dataclass
class PresetMetadata:
    """Metadata for a Voicemeeter preset"""

    name: str
    description: str
    version: str
    created: str
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    voicemeeter_type: Optional[str] = None  # basic, banana, potato
    checksum: Optional[str] = None


@dataclass
class PresetParameter:
    """Individual parameter in a preset"""

    name: str
    value: Union[str, float, int]
    description: Optional[str] = None


@dataclass
class PresetStrip:
    """Strip configuration in a preset"""

    id: int
    parameters: List[PresetParameter]
    label: Optional[str] = None


@dataclass
class PresetBus:
    """Bus configuration in a preset"""

    id: int
    parameters: List[PresetParameter]
    label: Optional[str] = None


@dataclass
class PresetScenario:
    """Scenario configuration in a preset"""

    name: str
    description: str
    parameters: List[PresetParameter]


@dataclass
class VoicemeeterPreset:
    """Complete Voicemeeter preset structure"""

    metadata: PresetMetadata
    strips: List[PresetStrip]
    buses: List[PresetBus]
    scenarios: List[PresetScenario]

    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary"""
        return asdict(self)

    def calculate_checksum(self) -> str:
        """Calculate MD5 checksum of preset content"""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()


class PresetValidationError(Exception):
    """Exception raised when preset validation fails"""

    pass


class PresetManager:
    """Enhanced preset management system"""

    # JSON Schema for preset validation
    PRESET_SCHEMA = {
        "type": "object",
        "properties": {
            "metadata": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "version": {"type": "string", "pattern": r"^\d+\.\d+(\.\d+)?$"},
                    "created": {"type": "string"},
                    "author": {"type": ["string", "null"]},
                    "tags": {"type": ["array", "null"], "items": {"type": "string"}},
                    "voicemeeter_type": {
                        "type": ["string", "null"],
                        "enum": ["basic", "banana", "potato", None],
                    },
                    "checksum": {"type": ["string", "null"]},
                },
                "required": ["name", "description", "version", "created"],
            },
            "strips": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "minimum": 0},
                        "label": {"type": ["string", "null"]},
                        "parameters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "minLength": 1},
                                    "value": {"type": ["string", "number"]},
                                    "description": {"type": ["string", "null"]},
                                },
                                "required": ["name", "value"],
                            },
                        },
                    },
                    "required": ["id", "parameters"],
                },
            },
            "buses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "minimum": 0},
                        "label": {"type": ["string", "null"]},
                        "parameters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "minLength": 1},
                                    "value": {"type": ["string", "number"]},
                                    "description": {"type": ["string", "null"]},
                                },
                                "required": ["name", "value"],
                            },
                        },
                    },
                    "required": ["id", "parameters"],
                },
            },
            "scenarios": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "description": {"type": "string"},
                        "parameters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "minLength": 1},
                                    "value": {"type": ["string", "number"]},
                                    "description": {"type": ["string", "null"]},
                                },
                                "required": ["name", "value"],
                            },
                        },
                    },
                    "required": ["name", "description", "parameters"],
                },
            },
        },
        "required": ["metadata", "strips", "buses", "scenarios"],
    }

    def __init__(
        self, preset_dir: str = "presets", backup_dir: str = "presets/backups"
    ):
        """Initialize preset manager

        Args:
            preset_dir: Directory containing preset files
            backup_dir: Directory for backup files
        """
        self.preset_dir = Path(preset_dir)
        self.backup_dir = Path(backup_dir)

        # Create directories if they don't exist
        self.preset_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"PresetManager initialized with preset_dir={preset_dir}, backup_dir={backup_dir}"
        )

    def validate_preset_schema(self, preset_data: Dict[str, Any]) -> None:
        """Validate preset data against JSON schema

        Args:
            preset_data: Preset data dictionary

        Raises:
            PresetValidationError: If validation fails
        """
        try:
            jsonschema.validate(preset_data, self.PRESET_SCHEMA)
            logger.debug("Preset schema validation passed")
        except jsonschema.ValidationError as e:
            error_msg = f"Preset validation failed: {e.message}"
            logger.error(error_msg)
            raise PresetValidationError(error_msg) from e

    def load_xml_preset(self, xml_path: str) -> VoicemeeterPreset:
        """Load preset from XML file and convert to structured format

        Args:
            xml_path: Path to XML preset file

        Returns:
            VoicemeeterPreset object

        Raises:
            PresetValidationError: If XML is invalid or malformed
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Extract metadata
            metadata_elem = root.find("metadata")
            if metadata_elem is None:
                raise PresetValidationError("Missing metadata section in XML preset")

            metadata = PresetMetadata(
                name=metadata_elem.findtext("name", ""),
                description=metadata_elem.findtext("description", ""),
                version=metadata_elem.findtext("version", "1.0"),
                created=metadata_elem.findtext("created", datetime.now().isoformat()),
                author=metadata_elem.findtext("author"),
                voicemeeter_type=metadata_elem.findtext("voicemeeter_type"),
            )

            # Extract tags if present
            tags_elem = metadata_elem.find("tags")
            if tags_elem is not None:
                metadata.tags = [
                    tag.text for tag in tags_elem.findall("tag") if tag.text
                ]

            # Extract strips
            strips = []
            strips_elem = root.find("strips")
            if strips_elem is not None:
                for strip_elem in strips_elem.findall("strip"):
                    strip_id = int(strip_elem.get("id", 0))
                    parameters = []

                    for param_elem in strip_elem.findall("param"):
                        param_name = param_elem.get("name")
                        param_value = param_elem.text

                        if param_name and param_value is not None:
                            # Try to convert to float if possible
                            try:
                                param_value = float(param_value)
                            except ValueError:
                                pass  # Keep as string

                            parameters.append(
                                PresetParameter(name=param_name, value=param_value)
                            )

                    strips.append(PresetStrip(id=strip_id, parameters=parameters))

            # Extract buses
            buses = []
            buses_elem = root.find("buses")
            if buses_elem is not None:
                for bus_elem in buses_elem.findall("bus"):
                    bus_id = int(bus_elem.get("id", 0))
                    parameters = []

                    for param_elem in bus_elem.findall("param"):
                        param_name = param_elem.get("name")
                        param_value = param_elem.text

                        if param_name and param_value is not None:
                            # Try to convert to float if possible
                            try:
                                param_value = float(param_value)
                            except ValueError:
                                pass  # Keep as string

                            parameters.append(
                                PresetParameter(name=param_name, value=param_value)
                            )

                    buses.append(PresetBus(id=bus_id, parameters=parameters))

            # Extract scenarios
            scenarios = []
            scenarios_elem = root.find("scenarios")
            if scenarios_elem is not None:
                for scenario_elem in scenarios_elem.findall("scenario"):
                    scenario_name = scenario_elem.get("name", "")
                    scenario_desc = scenario_elem.findtext("description", "")
                    parameters = []

                    params_elem = scenario_elem.find("params")
                    if params_elem is not None:
                        for param_elem in params_elem.findall("param"):
                            param_name = param_elem.get("name")
                            param_value = param_elem.text

                            if param_name and param_value is not None:
                                # Try to convert to float if possible
                                try:
                                    param_value = float(param_value)
                                except ValueError:
                                    pass  # Keep as string

                                parameters.append(
                                    PresetParameter(name=param_name, value=param_value)
                                )

                    scenarios.append(
                        PresetScenario(
                            name=scenario_name,
                            description=scenario_desc,
                            parameters=parameters,
                        )
                    )

            preset = VoicemeeterPreset(
                metadata=metadata, strips=strips, buses=buses, scenarios=scenarios
            )

            # Calculate and set checksum
            preset.metadata.checksum = preset.calculate_checksum()

            logger.info(f"Successfully loaded XML preset: {metadata.name}")
            return preset

        except ET.ParseError as e:
            error_msg = f"Invalid XML format in preset '{xml_path}': {str(e)}"
            logger.error(error_msg)
            raise PresetValidationError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to load XML preset '{xml_path}': {str(e)}"
            logger.error(error_msg)
            raise PresetValidationError(error_msg) from e

    def save_preset_json(self, preset: VoicemeeterPreset, json_path: str) -> None:
        """Save preset to JSON file

        Args:
            preset: VoicemeeterPreset object
            json_path: Path to save JSON file
        """
        preset_data = preset.to_dict()

        # Validate before saving
        self.validate_preset_schema(preset_data)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(preset_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Preset saved to JSON: {json_path}")

    def load_preset_json(self, json_path: str) -> VoicemeeterPreset:
        """Load preset from JSON file

        Args:
            json_path: Path to JSON preset file

        Returns:
            VoicemeeterPreset object

        Raises:
            PresetValidationError: If file not found or invalid
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                preset_data = json.load(f)
        except FileNotFoundError as e:
            error_msg = f"JSON preset file not found: {json_path}"
            logger.error(error_msg)
            raise PresetValidationError(error_msg) from e
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format in preset '{json_path}': {str(e)}"
            logger.error(error_msg)
            raise PresetValidationError(error_msg) from e

        # Validate schema
        self.validate_preset_schema(preset_data)

        # Convert to VoicemeeterPreset object
        metadata = PresetMetadata(**preset_data["metadata"])

        strips = [
            PresetStrip(
                id=strip_data["id"],
                label=strip_data.get("label"),
                parameters=[
                    PresetParameter(**param) for param in strip_data["parameters"]
                ],
            )
            for strip_data in preset_data["strips"]
        ]

        buses = [
            PresetBus(
                id=bus_data["id"],
                label=bus_data.get("label"),
                parameters=[
                    PresetParameter(**param) for param in bus_data["parameters"]
                ],
            )
            for bus_data in preset_data["buses"]
        ]

        scenarios = [
            PresetScenario(
                name=scenario_data["name"],
                description=scenario_data["description"],
                parameters=[
                    PresetParameter(**param) for param in scenario_data["parameters"]
                ],
            )
            for scenario_data in preset_data["scenarios"]
        ]

        preset = VoicemeeterPreset(
            metadata=metadata, strips=strips, buses=buses, scenarios=scenarios
        )

        logger.info(f"Successfully loaded JSON preset: {metadata.name}")
        return preset

    def create_backup(self, preset_path: str) -> str:
        """Create backup of preset file

        Args:
            preset_path: Path to preset file to backup

        Returns:
            Path to backup file
        """
        preset_file = Path(preset_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{preset_file.stem}_{timestamp}{preset_file.suffix}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(preset_path, backup_path)
        logger.info(f"Created backup: {backup_path}")

        return str(backup_path)

    def compare_presets(
        self, preset1: VoicemeeterPreset, preset2: VoicemeeterPreset
    ) -> Dict[str, Any]:
        """Compare two presets and return differences

        Args:
            preset1: First preset
            preset2: Second preset

        Returns:
            Dictionary containing comparison results
        """
        comparison = {
            "metadata_changes": {},
            "strip_changes": {},
            "bus_changes": {},
            "scenario_changes": {},
            "summary": {
                "total_changes": 0,
                "strips_modified": 0,
                "buses_modified": 0,
                "scenarios_modified": 0,
            },
        }

        # Compare metadata
        for field in ["name", "description", "version", "author", "voicemeeter_type"]:
            val1 = getattr(preset1.metadata, field)
            val2 = getattr(preset2.metadata, field)
            if val1 != val2:
                comparison["metadata_changes"][field] = {"old": val1, "new": val2}
                comparison["summary"]["total_changes"] += 1

        # Compare strips
        strips1_dict = {strip.id: strip for strip in preset1.strips}
        strips2_dict = {strip.id: strip for strip in preset2.strips}

        all_strip_ids = set(strips1_dict.keys()) | set(strips2_dict.keys())
        for strip_id in all_strip_ids:
            strip1 = strips1_dict.get(strip_id)
            strip2 = strips2_dict.get(strip_id)

            if strip1 is None:
                comparison["strip_changes"][strip_id] = {
                    "status": "added",
                    "parameters": strip2.parameters,
                }
                comparison["summary"]["strips_modified"] += 1
            elif strip2 is None:
                comparison["strip_changes"][strip_id] = {
                    "status": "removed",
                    "parameters": strip1.parameters,
                }
                comparison["summary"]["strips_modified"] += 1
            else:
                # Compare parameters
                params1_dict = {p.name: p.value for p in strip1.parameters}
                params2_dict = {p.name: p.value for p in strip2.parameters}

                param_changes = {}
                all_param_names = set(params1_dict.keys()) | set(params2_dict.keys())

                for param_name in all_param_names:
                    val1 = params1_dict.get(param_name)
                    val2 = params2_dict.get(param_name)

                    if val1 != val2:
                        param_changes[param_name] = {"old": val1, "new": val2}

                if param_changes:
                    comparison["strip_changes"][strip_id] = {
                        "status": "modified",
                        "parameter_changes": param_changes,
                    }
                    comparison["summary"]["strips_modified"] += 1

        # Compare buses (similar logic to strips)
        buses1_dict = {bus.id: bus for bus in preset1.buses}
        buses2_dict = {bus.id: bus for bus in preset2.buses}

        all_bus_ids = set(buses1_dict.keys()) | set(buses2_dict.keys())
        for bus_id in all_bus_ids:
            bus1 = buses1_dict.get(bus_id)
            bus2 = buses2_dict.get(bus_id)

            if bus1 is None:
                comparison["bus_changes"][bus_id] = {
                    "status": "added",
                    "parameters": bus2.parameters,
                }
                comparison["summary"]["buses_modified"] += 1
            elif bus2 is None:
                comparison["bus_changes"][bus_id] = {
                    "status": "removed",
                    "parameters": bus1.parameters,
                }
                comparison["summary"]["buses_modified"] += 1
            else:
                # Compare parameters
                params1_dict = {p.name: p.value for p in bus1.parameters}
                params2_dict = {p.name: p.value for p in bus2.parameters}

                param_changes = {}
                all_param_names = set(params1_dict.keys()) | set(params2_dict.keys())

                for param_name in all_param_names:
                    val1 = params1_dict.get(param_name)
                    val2 = params2_dict.get(param_name)

                    if val1 != val2:
                        param_changes[param_name] = {"old": val1, "new": val2}

                if param_changes:
                    comparison["bus_changes"][bus_id] = {
                        "status": "modified",
                        "parameter_changes": param_changes,
                    }
                    comparison["summary"]["buses_modified"] += 1

        # Compare scenarios
        scenarios1_dict = {scenario.name: scenario for scenario in preset1.scenarios}
        scenarios2_dict = {scenario.name: scenario for scenario in preset2.scenarios}

        all_scenario_names = set(scenarios1_dict.keys()) | set(scenarios2_dict.keys())
        for scenario_name in all_scenario_names:
            scenario1 = scenarios1_dict.get(scenario_name)
            scenario2 = scenarios2_dict.get(scenario_name)

            if scenario1 is None:
                comparison["scenario_changes"][scenario_name] = {
                    "status": "added",
                    "parameters": scenario2.parameters,
                }
                comparison["summary"]["scenarios_modified"] += 1
            elif scenario2 is None:
                comparison["scenario_changes"][scenario_name] = {
                    "status": "removed",
                    "parameters": scenario1.parameters,
                }
                comparison["summary"]["scenarios_modified"] += 1
            else:
                # Compare parameters
                params1_dict = {p.name: p.value for p in scenario1.parameters}
                params2_dict = {p.name: p.value for p in scenario2.parameters}

                param_changes = {}
                all_param_names = set(params1_dict.keys()) | set(params2_dict.keys())

                for param_name in all_param_names:
                    val1 = params1_dict.get(param_name)
                    val2 = params2_dict.get(param_name)

                    if val1 != val2:
                        param_changes[param_name] = {"old": val1, "new": val2}

                if param_changes:
                    comparison["scenario_changes"][scenario_name] = {
                        "status": "modified",
                        "parameter_changes": param_changes,
                    }
                    comparison["summary"]["scenarios_modified"] += 1

        # Update total changes
        comparison["summary"]["total_changes"] = (
            len(comparison["metadata_changes"])
            + comparison["summary"]["strips_modified"]
            + comparison["summary"]["buses_modified"]
            + comparison["summary"]["scenarios_modified"]
        )

        logger.info(
            f"Preset comparison completed: {comparison['summary']['total_changes']} total changes"
        )
        return comparison

    def list_presets(self, extension: str = None) -> List[Dict[str, str]]:
        """List all preset files in preset directory

        Args:
            extension: Filter by file extension (e.g., '.xml', '.json')

        Returns:
            List of preset file information
        """
        presets = []

        for preset_file in self.preset_dir.iterdir():
            if preset_file.is_file():
                if extension is None or preset_file.suffix.lower() == extension.lower():
                    presets.append(
                        {
                            "name": preset_file.stem,
                            "path": str(preset_file),
                            "extension": preset_file.suffix,
                            "size": preset_file.stat().st_size,
                            "modified": datetime.fromtimestamp(
                                preset_file.stat().st_mtime
                            ).isoformat(),
                        }
                    )

        return sorted(presets, key=lambda x: x["modified"], reverse=True)

    def list_backups(self) -> List[Dict[str, str]]:
        """List all backup files

        Returns:
            List of backup file information
        """
        backups = []

        for backup_file in self.backup_dir.iterdir():
            if backup_file.is_file():
                backups.append(
                    {
                        "name": backup_file.stem,
                        "path": str(backup_file),
                        "extension": backup_file.suffix,
                        "size": backup_file.stat().st_size,
                        "created": datetime.fromtimestamp(
                            backup_file.stat().st_ctime
                        ).isoformat(),
                    }
                )

        return sorted(backups, key=lambda x: x["created"], reverse=True)

    def create_template(
        self, template_name: str, voicemeeter_type: str = "potato"
    ) -> VoicemeeterPreset:
        """Create a preset template for specific Voicemeeter type

        Args:
            template_name: Name for the template
            voicemeeter_type: Type of Voicemeeter (basic, banana, potato)

        Returns:
            VoicemeeterPreset template
        """
        # Define strip and bus counts for each Voicemeeter type
        type_config = {
            "basic": {"strips": 3, "buses": 2},
            "banana": {"strips": 5, "buses": 3},
            "potato": {"strips": 8, "buses": 5},
        }

        config = type_config.get(voicemeeter_type, type_config["potato"])

        metadata = PresetMetadata(
            name=template_name,
            description=f"Template for Voicemeeter {voicemeeter_type.title()}",
            version="1.0",
            created=datetime.now().isoformat(),
            voicemeeter_type=voicemeeter_type,
        )

        # Create default strips
        strips = []
        for i in range(config["strips"]):
            parameters = [
                PresetParameter(name=f"Strip[{i}].label", value=f"Strip {i+1}"),
                PresetParameter(name=f"Strip[{i}].mute", value=0.0),
                PresetParameter(name=f"Strip[{i}].gain", value=0.0),
                PresetParameter(name=f"Strip[{i}].A1", value=1.0),
                PresetParameter(name=f"Strip[{i}].A2", value=0.0),
            ]

            if i < 2:  # First two strips have additional parameters
                parameters.extend(
                    [
                        PresetParameter(name=f"Strip[{i}].B1", value=0.0),
                        PresetParameter(name=f"Strip[{i}].comp", value=0.0),
                        PresetParameter(name=f"Strip[{i}].gate", value=0.0),
                    ]
                )

            strips.append(PresetStrip(id=i, parameters=parameters))

        # Create default buses
        buses = []
        for i in range(config["buses"]):
            parameters = [
                PresetParameter(name=f"Bus[{i}].mute", value=0.0),
                PresetParameter(name=f"Bus[{i}].gain", value=0.0),
                PresetParameter(name=f"Bus[{i}].eq.on", value=0.0),
            ]

            buses.append(PresetBus(id=i, parameters=parameters))

        # Create default scenarios
        scenarios = [
            PresetScenario(
                name="default", description="Default configuration", parameters=[]
            )
        ]

        preset = VoicemeeterPreset(
            metadata=metadata, strips=strips, buses=buses, scenarios=scenarios
        )

        # Calculate and set checksum
        preset.metadata.checksum = preset.calculate_checksum()

        logger.info(f"Created template preset: {template_name} for {voicemeeter_type}")
        return preset

    def restore_from_backup(self, backup_path: str, target_path: str) -> None:
        """Restore preset from backup

        Args:
            backup_path: Path to backup file
            target_path: Path to restore to
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        shutil.copy2(backup_path, target_path)
        logger.info(f"Restored preset from backup: {backup_path} -> {target_path}")

    def cleanup_old_backups(self, max_backups: int = 10) -> List[str]:
        """Clean up old backup files, keeping only the most recent ones

        Args:
            max_backups: Maximum number of backups to keep per preset

        Returns:
            List of deleted backup file paths
        """
        backups = self.list_backups()
        deleted_files = []

        # Group backups by original preset name (before timestamp)
        backup_groups = {}
        for backup in backups:
            # Extract original name by removing timestamp suffix
            name_parts = backup["name"].split("_")
            if len(name_parts) >= 3:  # name_YYYYMMDD_HHMMSS
                original_name = "_".join(name_parts[:-2])
                if original_name not in backup_groups:
                    backup_groups[original_name] = []
                backup_groups[original_name].append(backup)

        # Keep only max_backups for each preset
        for original_name, group_backups in backup_groups.items():
            # Sort by creation time (newest first)
            group_backups.sort(key=lambda x: x["created"], reverse=True)

            # Delete excess backups
            for backup in group_backups[max_backups:]:
                try:
                    os.remove(backup["path"])
                    deleted_files.append(backup["path"])
                    logger.info(f"Deleted old backup: {backup['path']}")
                except OSError as e:
                    logger.error(f"Failed to delete backup {backup['path']}: {e}")

        return deleted_files

    def export_preset_xml(self, preset: VoicemeeterPreset, xml_path: str) -> None:
        """Export preset to XML format

        Args:
            preset: VoicemeeterPreset object
            xml_path: Path to save XML file
        """
        root = Element("voicemeeter_preset")

        # Add metadata
        metadata_elem = SubElement(root, "metadata")
        SubElement(metadata_elem, "name").text = preset.metadata.name
        SubElement(metadata_elem, "description").text = preset.metadata.description
        SubElement(metadata_elem, "version").text = preset.metadata.version
        SubElement(metadata_elem, "created").text = preset.metadata.created

        if preset.metadata.author:
            SubElement(metadata_elem, "author").text = preset.metadata.author
        if preset.metadata.voicemeeter_type:
            SubElement(metadata_elem, "voicemeeter_type").text = (
                preset.metadata.voicemeeter_type
            )

        if preset.metadata.tags:
            tags_elem = SubElement(metadata_elem, "tags")
            for tag in preset.metadata.tags:
                SubElement(tags_elem, "tag").text = tag

        # Add strips
        strips_elem = SubElement(root, "strips")
        for strip in preset.strips:
            strip_elem = SubElement(strips_elem, "strip", id=str(strip.id))
            for param in strip.parameters:
                param_elem = SubElement(strip_elem, "param", name=param.name)
                param_elem.text = str(param.value)

        # Add buses
        buses_elem = SubElement(root, "buses")
        for bus in preset.buses:
            bus_elem = SubElement(buses_elem, "bus", id=str(bus.id))
            for param in bus.parameters:
                param_elem = SubElement(bus_elem, "param", name=param.name)
                param_elem.text = str(param.value)

        # Add scenarios
        scenarios_elem = SubElement(root, "scenarios")
        for scenario in preset.scenarios:
            scenario_elem = SubElement(
                scenarios_elem, "scenario", name=scenario.name
            )
            SubElement(scenario_elem, "description").text = scenario.description

            params_elem = SubElement(scenario_elem, "params")
            for param in scenario.parameters:
                param_elem = SubElement(params_elem, "param", name=param.name)
                param_elem.text = str(param.value)

        # Write to file with proper formatting
        tree = ElementTree(root)
        indent(tree, space="    ", level=0)
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)

        logger.info(f"Preset exported to XML: {xml_path}")
