"""Importer pour le standard REFI-QDA (Qualitative Data Analysis Exchange)."""

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional

from .base import BaseImporter, ImportResult
from ..models.source import Source, SourceType
from ..models.node import Node
from ..models.coding import CodeReference


class RefiQdaImporter(BaseImporter):
    """Importe les projets au format REFI-QDA (.qdpx)."""

    def import_file(
        self,
        file_path: Path,
        project_files_path: Path,
        **options,
    ) -> ImportResult:
        """
        Importe un projet REFI-QDA.

        Note: Cette méthode retourne les informations du projet.
        Pour un import complet, utilisez import_project().
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        valid, error = self.validate_file(file_path)
        if not valid:
            return ImportResult(success=False, error=error)

        try:
            self.report_progress(0.1, "Ouverture du fichier QDPX...")

            project_info = self._parse_qdpx(file_path)

            self.report_progress(1.0, "Analyse terminée")

            # Retourner les infos comme métadonnées
            return ImportResult(
                success=True,
                source=None,  # Pas de source unique pour un projet complet
                metadata=project_info,
            )

        except Exception as e:
            return ImportResult(success=False, error=str(e))

    def import_project(self, file_path: Path, project) -> dict:
        """
        Importe un projet REFI-QDA complet dans un projet Lele.

        Args:
            file_path: Chemin du fichier .qdpx
            project: Instance de Project Lele

        Returns:
            Dictionnaire avec les statistiques d'import
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        stats = {
            "sources_imported": 0,
            "nodes_imported": 0,
            "codes_imported": 0,
            "errors": [],
        }

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # Lire le fichier project.qde
                qde_content = zf.read("project.qde").decode("utf-8")
                root = ET.fromstring(qde_content)

                ns = self._get_namespaces(root)

                # Importer les sources
                self._import_sources(zf, root, ns, project, stats)

                # Importer les codes (nœuds)
                self._import_codes(root, ns, project, stats)

                # Importer les codages
                self._import_codings(root, ns, project, stats)

        except Exception as e:
            stats["errors"].append(f"Erreur globale: {e}")

        return stats

    def _parse_qdpx(self, file_path: Path) -> dict:
        """Parse un fichier QDPX et retourne les informations du projet."""
        info = {
            "name": "",
            "created": "",
            "modified": "",
            "sources": [],
            "codes": [],
            "users": [],
        }

        with zipfile.ZipFile(file_path, "r") as zf:
            # Liste des fichiers dans l'archive
            info["files"] = zf.namelist()

            # Lire le fichier project.qde
            if "project.qde" in zf.namelist():
                qde_content = zf.read("project.qde").decode("utf-8")
                root = ET.fromstring(qde_content)

                ns = self._get_namespaces(root)

                # Informations du projet
                project_elem = root.find(".//Project", ns) or root
                info["name"] = project_elem.get("name", "")
                info["created"] = project_elem.get("creationDateTime", "")
                info["modified"] = project_elem.get("modifiedDateTime", "")

                # Sources
                for source in root.findall(".//Source", ns) or root.findall(".//Sources/Source", ns):
                    info["sources"].append({
                        "guid": source.get("guid", ""),
                        "name": source.get("name", ""),
                        "type": source.get("type", ""),
                    })

                # Codes
                for code in root.findall(".//Code", ns) or root.findall(".//Codes/Code", ns):
                    info["codes"].append({
                        "guid": code.get("guid", ""),
                        "name": code.get("name", ""),
                        "color": code.get("color", ""),
                    })

                # Utilisateurs
                for user in root.findall(".//User", ns) or root.findall(".//Users/User", ns):
                    info["users"].append({
                        "guid": user.get("guid", ""),
                        "name": user.get("name", ""),
                    })

        return info

    def _get_namespaces(self, root) -> dict:
        """Extrait les namespaces du document XML."""
        ns = {}
        if root.tag.startswith("{"):
            ns_uri = root.tag[1:root.tag.index("}")]
            ns[""] = ns_uri
        return ns

    def _import_sources(self, zf, root, ns, project, stats):
        """Importe les sources depuis le projet REFI-QDA."""
        sources_elem = root.find(".//Sources", ns) or root.findall(".//Source", ns)
        if sources_elem is None:
            sources_elem = root.findall(".//Source", ns)
        else:
            sources_elem = sources_elem.findall("Source", ns)

        for source_elem in sources_elem:
            try:
                guid = source_elem.get("guid", "")
                name = source_elem.get("name", "Unnamed")
                source_type = source_elem.get("type", "")

                # Déterminer le type de source
                lele_type = self._map_source_type(source_type)

                # Chercher le contenu textuel
                content = ""
                text_elem = source_elem.find(".//PlainTextContent", ns)
                if text_elem is not None and text_elem.text:
                    content = text_elem.text

                # Chercher le fichier associé
                file_path_elem = source_elem.get("path", "")
                internal_path = None

                if file_path_elem and file_path_elem in zf.namelist():
                    # Extraire le fichier
                    internal_path = project.files_path / Path(file_path_elem).name
                    with zf.open(file_path_elem) as src_file:
                        internal_path.write_bytes(src_file.read())

                # Créer la source
                source = Source(
                    id=guid,
                    name=name,
                    type=lele_type,
                    file_path=str(internal_path) if internal_path else None,
                    content=content,
                    metadata={"refi_qda_guid": guid, "original_type": source_type},
                )
                source.save(project.db)
                stats["sources_imported"] += 1

            except Exception as e:
                stats["errors"].append(f"Source {name}: {e}")

    def _import_codes(self, root, ns, project, stats, parent_id=None, parent_elem=None):
        """Importe les codes (nœuds) depuis le projet REFI-QDA."""
        if parent_elem is None:
            codes_elem = root.find(".//Codes", ns)
            if codes_elem is None:
                codes_elem = root
            code_elems = codes_elem.findall("Code", ns) or codes_elem.findall(".//Code", ns)
        else:
            code_elems = parent_elem.findall("Code", ns)

        for code_elem in code_elems:
            try:
                guid = code_elem.get("guid", "")
                name = code_elem.get("name", "Unnamed")
                color = code_elem.get("color", "#3498db")
                description = ""

                desc_elem = code_elem.find("Description", ns)
                if desc_elem is not None and desc_elem.text:
                    description = desc_elem.text

                # Normaliser la couleur
                if color and not color.startswith("#"):
                    color = f"#{color}"

                # Créer le nœud
                node = Node(
                    id=guid,
                    name=name,
                    description=description,
                    color=color,
                    parent_id=parent_id,
                )
                node.save(project.db)
                stats["nodes_imported"] += 1

                # Importer les sous-codes récursivement
                self._import_codes(root, ns, project, stats, parent_id=guid, parent_elem=code_elem)

            except Exception as e:
                stats["errors"].append(f"Code {name}: {e}")

    def _import_codings(self, root, ns, project, stats):
        """Importe les références de codage depuis le projet REFI-QDA."""
        codings_elem = root.find(".//Coding", ns) or root.findall(".//CodeRef", ns)

        if codings_elem is None:
            return

        if hasattr(codings_elem, "findall"):
            code_refs = codings_elem.findall("CodeRef", ns)
        else:
            code_refs = codings_elem

        for coding_elem in code_refs:
            try:
                code_guid = coding_elem.get("targetGUID", "")

                # Trouver les références de texte
                for text_ref in coding_elem.findall(".//TextReference", ns):
                    source_guid = text_ref.get("sourceGUID", "")
                    start = int(text_ref.get("start", 0))
                    end = int(text_ref.get("end", 0))

                    code_ref = CodeReference(
                        node_id=code_guid,
                        source_id=source_guid,
                        start_pos=start,
                        end_pos=end,
                    )
                    code_ref.save(project.db)
                    stats["codes_imported"] += 1

            except Exception as e:
                stats["errors"].append(f"Coding: {e}")

    def _map_source_type(self, refi_type: str) -> SourceType:
        """Mappe un type REFI-QDA vers un type Lele."""
        type_map = {
            "TextSource": SourceType.TEXT,
            "PDFSource": SourceType.PDF,
            "AudioSource": SourceType.AUDIO,
            "VideoSource": SourceType.VIDEO,
            "ImageSource": SourceType.IMAGE,
        }
        return type_map.get(refi_type, SourceType.OTHER)

    def export_project(self, project, output_path: Path) -> bool:
        """
        Exporte un projet Lele au format REFI-QDA.

        Args:
            project: Instance de Project Lele
            output_path: Chemin du fichier .qdpx à créer

        Returns:
            True si l'export a réussi
        """
        from datetime import datetime

        try:
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Créer le document XML principal
                root = ET.Element("Project")
                root.set("name", project.name)
                root.set("creationDateTime", project.created_at.isoformat())
                root.set("modifiedDateTime", datetime.now().isoformat())

                # Ajouter les sources
                sources_elem = ET.SubElement(root, "Sources")
                for source in Source.get_all(project.db):
                    source_elem = ET.SubElement(sources_elem, "Source")
                    source_elem.set("guid", source.id)
                    source_elem.set("name", source.name)
                    source_elem.set("type", f"{source.type.value.title()}Source")

                    if source.content:
                        text_elem = ET.SubElement(source_elem, "PlainTextContent")
                        text_elem.text = source.content

                # Ajouter les codes
                codes_elem = ET.SubElement(root, "Codes")
                self._export_nodes_recursive(project.db, codes_elem, None)

                # Ajouter les codages
                # ... (implémentation similaire)

                # Écrire le fichier project.qde
                xml_str = ET.tostring(root, encoding="unicode")
                zf.writestr("project.qde", xml_str)

            return True

        except Exception:
            return False

    def _export_nodes_recursive(self, db, parent_elem, parent_id):
        """Exporte les nœuds récursivement."""
        nodes = Node.get_all(db, parent_id=parent_id)
        for node in nodes:
            code_elem = ET.SubElement(parent_elem, "Code")
            code_elem.set("guid", node.id)
            code_elem.set("name", node.name)
            code_elem.set("color", node.color.lstrip("#"))

            if node.description:
                desc_elem = ET.SubElement(code_elem, "Description")
                desc_elem.text = node.description

            # Enfants récursivement
            self._export_nodes_recursive(db, code_elem, node.id)
