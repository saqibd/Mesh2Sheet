from __future__ import annotations

from dataclasses import dataclass

import bmesh
import bpy

from .panel_detector import PanelDetectionResult


@dataclass
class PanelConnection:
    panel_a: int
    panel_b: int
    shared_edge_count: int
    shared_edge_indices: list[tuple[int, int]]
    shared_edge_length: float


@dataclass
class PanelGraphResult:
    connections: list[PanelConnection]
    connection_count: int
    isolated_panels: int
    average_connections_per_panel: float


class PanelGraph:
    """Build a lightweight panel connectivity graph from detected panels."""

    def build(self, obj: bpy.types.Object | None, panel_result: PanelDetectionResult) -> PanelGraphResult:
        if obj is None or obj.type != "MESH" or obj.data is None:
            print("PanelGraph diagnostics: object is not a mesh; no graph built")
            return PanelGraphResult([], 0, 0, 0.0)

        bm = bmesh.new()
        try:
            bm.from_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.verts.ensure_lookup_table()

            faces = list(bm.faces)
            face_index_lookup = {id(face): face_index for face_index, face in enumerate(faces)}

            print("PanelGraph diagnostics")
            print("")
            print("Panels received:")
            print(panel_result.panel_count)
            print("")
            print("Face->panel lookup entries:")
            face_to_panel: dict[int, int] = {}
            for panel in panel_result.panels:
                for face_index in panel.face_indices:
                    face_to_panel[face_index] = panel.panel_id

            print(len(face_to_panel))
            print("")
            print("Total mesh edges:")
            total_edges = len(bm.edges)
            print(total_edges)
            print("")

            connections_by_pair: dict[tuple[int, int], PanelConnection] = {}
            valid_two_face_edges = 0
            skipped_edges = 0
            same_panel_edges = 0
            different_panel_edges = 0
            missing_face_lookup_count = 0
            connection_created_count = 0

            for edge in bm.edges:
                if len(edge.link_faces) != 2:
                    skipped_edges += 1
                    continue

                valid_two_face_edges += 1

                face_a_index = face_index_lookup.get(id(edge.link_faces[0]))
                face_b_index = face_index_lookup.get(id(edge.link_faces[1]))
                if face_a_index is None or face_b_index is None:
                    missing_face_lookup_count += 1
                    continue

                panel_a = face_to_panel.get(face_a_index)
                panel_b = face_to_panel.get(face_b_index)
                if panel_a is None or panel_b is None:
                    continue

                if panel_a == panel_b:
                    same_panel_edges += 1
                    continue

                different_panel_edges += 1
                connection_key = (panel_a, panel_b) if panel_a < panel_b else (panel_b, panel_a)
                connection = connections_by_pair.get(connection_key)
                if connection is None:
                    connection_created_count += 1
                    connection = PanelConnection(
                        panel_a=connection_key[0],
                        panel_b=connection_key[1],
                        shared_edge_count=0,
                        shared_edge_indices=[],
                        shared_edge_length=0.0,
                    )
                    connections_by_pair[connection_key] = connection

                connection.shared_edge_count += 1
                connection.shared_edge_indices.append((edge.verts[0].index, edge.verts[1].index))
                connection.shared_edge_length += edge.calc_length()

            print("Edges with exactly two linked faces:")
            print(valid_two_face_edges)
            print("")
            print("Edges skipped:")
            print(skipped_edges)
            print("")
            print("Edges with adjacent faces in the same panel:")
            print(same_panel_edges)
            print("")
            print("Edges with adjacent faces in different panels:")
            print(different_panel_edges)
            print("")
            print("Connections created:")
            print(connection_created_count)
            print("")
            print("Face lookup misses:")
            print(missing_face_lookup_count)
            print("")

            ordered_connections = [
                connections_by_pair[key]
                for key in sorted(connections_by_pair.keys(), key=lambda item: (item[0], item[1]))
            ]

            connected_panel_ids = {connection.panel_a for connection in ordered_connections}
            connected_panel_ids.update(connection.panel_b for connection in ordered_connections)
            isolated_panels = sum(
                1
                for panel in panel_result.panels
                if panel.panel_id not in connected_panel_ids
            )

            connection_count = len(ordered_connections)
            average_connections_per_panel = (
                connection_count / panel_result.panel_count if panel_result.panel_count else 0.0
            )

            print("Diagnostic summary")
            print("")
            print("Connections:")
            print(connection_count)
            print("")
            print("Isolated panels:")
            print(isolated_panels)
            print("")
            print("Average connections per panel:")
            print(f"{average_connections_per_panel:.2f}")
            print("")
            print("PanelGraph diagnostics complete")

            return PanelGraphResult(
                connections=ordered_connections,
                connection_count=connection_count,
                isolated_panels=isolated_panels,
                average_connections_per_panel=average_connections_per_panel,
            )
        finally:
            bm.free()
