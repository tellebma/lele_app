"""Importer pour les fichiers bibliographiques (Zotero, EndNote, Citavi, etc.)."""

import re
from pathlib import Path
from typing import Optional

from .base import BaseImporter, ImportResult
from ..models.source import Source, SourceType


class BibliographyImporter(BaseImporter):
    """Importe les fichiers de références bibliographiques."""

    source_type = SourceType.BIBLIOGRAPHY

    def import_file(
        self,
        file_path: Path,
        project_files_path: Path,
        **options,
    ) -> ImportResult:
        """Importe un fichier bibliographique."""
        if isinstance(file_path, str):
            file_path = Path(file_path)

        valid, error = self.validate_file(file_path)
        if not valid:
            return ImportResult(success=False, error=error)

        warnings = []
        extra_metadata = {}

        try:
            self.report_progress(0.1, "Analyse du fichier...")

            ext = file_path.suffix.lower()

            if ext == ".ris":
                references, content = self._parse_ris(file_path)
            elif ext == ".bib":
                references, content = self._parse_bibtex(file_path)
            elif ext == ".enw":
                references, content = self._parse_endnote(file_path)
            elif ext == ".xml":
                references, content = self._parse_xml(file_path)
            else:
                return ImportResult(
                    success=False,
                    error=f"Format bibliographique non supporté: {ext}",
                )

            extra_metadata["reference_count"] = len(references)
            extra_metadata["references"] = references

            self.report_progress(0.6, "Copie du fichier...")

            # Copier dans le projet
            dest_path = self.copy_to_project(file_path, project_files_path)

            self.report_progress(0.9, "Création de la source...")

            # Créer la source
            metadata = self.get_file_metadata(file_path)
            metadata.update(extra_metadata)

            source = Source(
                name=file_path.stem,
                type=SourceType.BIBLIOGRAPHY,
                file_path=str(dest_path),
                content=content,
                metadata=metadata,
            )

            self.report_progress(1.0, "Import terminé")

            return ImportResult(
                success=True,
                source=source,
                warnings=warnings,
                metadata=metadata,
            )

        except Exception as e:
            return ImportResult(success=False, error=str(e))

    def _parse_ris(self, file_path: Path) -> tuple[list[dict], str]:
        """Parse un fichier RIS (Research Information Systems)."""
        content = file_path.read_text(encoding="utf-8-sig")
        references = []
        current_ref = {}
        current_field = None

        # Mapping des champs RIS
        field_map = {
            "TY": "type",
            "TI": "title",
            "T1": "title",
            "AU": "authors",
            "A1": "authors",
            "PY": "year",
            "Y1": "year",
            "AB": "abstract",
            "N2": "abstract",
            "JO": "journal",
            "JF": "journal",
            "VL": "volume",
            "IS": "issue",
            "SP": "start_page",
            "EP": "end_page",
            "DO": "doi",
            "UR": "url",
            "KW": "keywords",
        }

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            if line == "ER  -":  # End of reference
                if current_ref:
                    references.append(current_ref)
                current_ref = {}
                current_field = None
            elif "  - " in line:
                tag = line[:2]
                value = line[6:].strip()
                field = field_map.get(tag)

                if field:
                    current_field = field
                    if field == "authors" or field == "keywords":
                        if field not in current_ref:
                            current_ref[field] = []
                        current_ref[field].append(value)
                    else:
                        current_ref[field] = value
            elif current_field and line:
                # Continuation de la ligne précédente
                if isinstance(current_ref.get(current_field), list):
                    current_ref[current_field][-1] += " " + line
                else:
                    current_ref[current_field] += " " + line

        if current_ref:
            references.append(current_ref)

        # Créer le contenu texte
        text_parts = []
        for ref in references:
            text_parts.append(self._format_reference(ref))

        return references, "\n\n".join(text_parts)

    def _parse_bibtex(self, file_path: Path) -> tuple[list[dict], str]:
        """Parse un fichier BibTeX."""
        content = file_path.read_text(encoding="utf-8-sig")
        references = []

        # Regex pour extraire les entrées
        entry_pattern = re.compile(
            r"@(\w+)\s*\{\s*([^,]+)\s*,\s*(.*?)\s*\}(?=\s*@|\s*$)",
            re.DOTALL,
        )

        field_pattern = re.compile(r"(\w+)\s*=\s*[{\"](.+?)[}\"]", re.DOTALL)

        for match in entry_pattern.finditer(content):
            entry_type = match.group(1).lower()
            cite_key = match.group(2).strip()
            fields_str = match.group(3)

            ref = {"type": entry_type, "cite_key": cite_key}

            for field_match in field_pattern.finditer(fields_str):
                field_name = field_match.group(1).lower()
                field_value = field_match.group(2).strip()

                # Nettoyer les caractères LaTeX basiques
                field_value = field_value.replace("\\&", "&")
                field_value = field_value.replace("~", " ")

                if field_name == "author":
                    # Séparer les auteurs
                    authors = [a.strip() for a in field_value.split(" and ")]
                    ref["authors"] = authors
                elif field_name == "keywords":
                    ref["keywords"] = [k.strip() for k in field_value.split(",")]
                else:
                    ref[field_name] = field_value

            references.append(ref)

        # Créer le contenu texte
        text_parts = []
        for ref in references:
            text_parts.append(self._format_reference(ref))

        return references, "\n\n".join(text_parts)

    def _parse_endnote(self, file_path: Path) -> tuple[list[dict], str]:
        """Parse un fichier EndNote (.enw)."""
        content = file_path.read_text(encoding="utf-8-sig")
        references = []
        current_ref = {}

        # Format EndNote est similaire à RIS
        field_map = {
            "%0": "type",
            "%T": "title",
            "%A": "authors",
            "%D": "year",
            "%X": "abstract",
            "%J": "journal",
            "%V": "volume",
            "%N": "issue",
            "%P": "pages",
            "%R": "doi",
            "%U": "url",
            "%K": "keywords",
        }

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                if current_ref:
                    references.append(current_ref)
                    current_ref = {}
                continue

            if line.startswith("%"):
                tag = line[:2]
                value = line[3:].strip()
                field = field_map.get(tag)

                if field:
                    if field == "authors" or field == "keywords":
                        if field not in current_ref:
                            current_ref[field] = []
                        current_ref[field].append(value)
                    else:
                        current_ref[field] = value

        if current_ref:
            references.append(current_ref)

        # Créer le contenu texte
        text_parts = []
        for ref in references:
            text_parts.append(self._format_reference(ref))

        return references, "\n\n".join(text_parts)

    def _parse_xml(self, file_path: Path) -> tuple[list[dict], str]:
        """Parse un fichier XML bibliographique (Zotero, etc.)."""
        import xml.etree.ElementTree as ET

        tree = ET.parse(file_path)
        root = tree.getroot()
        references = []

        # Détecter le format
        if "zotero" in root.tag.lower() or root.tag == "xml":
            references = self._parse_zotero_xml(root)
        elif "mods" in root.tag.lower():
            references = self._parse_mods_xml(root)
        else:
            # Format générique
            for item in root.iter():
                if "record" in item.tag.lower() or "item" in item.tag.lower():
                    ref = {}
                    for child in item:
                        tag = child.tag.split("}")[-1].lower()  # Remove namespace
                        ref[tag] = child.text
                    if ref:
                        references.append(ref)

        # Créer le contenu texte
        text_parts = []
        for ref in references:
            text_parts.append(self._format_reference(ref))

        return references, "\n\n".join(text_parts)

    def _parse_zotero_xml(self, root) -> list[dict]:
        """Parse le format XML Zotero."""
        references = []
        ns = {"z": "http://www.zotero.org/namespaces/export#"}

        for item in root.findall(".//z:item", ns) or root.iter():
            if "item" in str(item.tag).lower():
                ref = {}
                for child in item:
                    tag = child.tag.split("}")[-1].lower()
                    if child.text:
                        ref[tag] = child.text
                if ref:
                    references.append(ref)

        return references

    def _parse_mods_xml(self, root) -> list[dict]:
        """Parse le format MODS XML."""
        references = []
        ns = {"mods": "http://www.loc.gov/mods/v3"}

        for mods in root.findall(".//mods:mods", ns) or [root]:
            ref = {}

            title = mods.find(".//mods:title", ns)
            if title is not None and title.text:
                ref["title"] = title.text

            for name in mods.findall(".//mods:name", ns):
                name_parts = name.findall(".//mods:namePart", ns)
                if name_parts:
                    author = " ".join(p.text for p in name_parts if p.text)
                    if "authors" not in ref:
                        ref["authors"] = []
                    ref["authors"].append(author)

            date = mods.find(".//mods:dateIssued", ns)
            if date is not None and date.text:
                ref["year"] = date.text[:4]

            abstract = mods.find(".//mods:abstract", ns)
            if abstract is not None and abstract.text:
                ref["abstract"] = abstract.text

            if ref:
                references.append(ref)

        return references

    def _format_reference(self, ref: dict) -> str:
        """Formate une référence en texte lisible."""
        parts = []

        # Auteurs
        authors = ref.get("authors", [])
        if authors:
            if isinstance(authors, list):
                parts.append(", ".join(authors))
            else:
                parts.append(authors)

        # Année
        year = ref.get("year")
        if year:
            parts.append(f"({year})")

        # Titre
        title = ref.get("title")
        if title:
            parts.append(f'"{title}"')

        # Journal
        journal = ref.get("journal")
        if journal:
            parts.append(journal)

        # Volume/Issue
        volume = ref.get("volume")
        issue = ref.get("issue")
        if volume:
            vol_str = volume
            if issue:
                vol_str += f"({issue})"
            parts.append(vol_str)

        # Pages
        pages = ref.get("pages") or ref.get("start_page")
        if pages:
            end_page = ref.get("end_page")
            if end_page:
                pages = f"{pages}-{end_page}"
            parts.append(f"pp. {pages}")

        # DOI
        doi = ref.get("doi")
        if doi:
            parts.append(f"DOI: {doi}")

        result = ". ".join(str(p) for p in parts if p)

        # Abstract
        abstract = ref.get("abstract")
        if abstract:
            result += f"\n\nRésumé: {abstract}"

        return result
