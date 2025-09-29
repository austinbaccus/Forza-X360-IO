from typing import List
from utils.forza_version import ForzaVersion

class ForzaTrackSection:
    def __init__(self, forza_version: ForzaVersion):
        self.SubSections: List["ForzaTrackSubSection"] = []
        self.Name: str = ""
        self.Type: str = ""
        self.Offset: "Vector3" = Vector3(0.0, 0.0, 0.0)

        # Header / transforms (pattern of 1, vec3, 0.0, vec3, 0.0, vec3, 0.0, 1)
        Utilities.assert_equals(self.Stream.read_uint32(), 1)
        _ = Vector3(self.Stream.read_single(), self.Stream.read_single(), self.Stream.read_single())
        Utilities.assert_equals(self.Stream.read_single(), 0.0)
        _ = Vector3(self.Stream.read_single(), self.Stream.read_single(), self.Stream.read_single())
        Utilities.assert_equals(self.Stream.read_single(), 0.0)
        _ = Vector3(self.Stream.read_single(), self.Stream.read_single(), self.Stream.read_single())
        Utilities.assert_equals(self.Stream.read_single(), 0.0)
        Utilities.assert_equals(self.Stream.read_uint32(), 1)

        # Name/type
        name_len = self.Stream.read_int32()
        self.Name = self.Stream.read_ascii(name_len).lower()
        parts = self.Name.split('_')
        self.Type = parts[0].lower()
        self.Name = self.Name[self.Name.index('_') + 1:]

        # Vertex block
        Utilities.assert_equals(self.Stream.read_uint32(), 2)
        num = self.Stream.read_uint32()
        size = self.Stream.read_uint32()

        base_vertices: List["ForzaVertex"] = [None] * num  # type: ignore
        for i in range(num):
            base_vertices[i] = ForzaVertex(forza_version, ForzaVertexType.Track, self.Stream, size)

        Utilities.assert_equals(self.Stream.read_uint32(), 1)
        BoundingBox.from_vertices(base_vertices)

        # Subsections
        sub_count = self.Stream.read_uint32()
        self.SubSections = [None] * sub_count  # type: ignore

        for j in range(sub_count):
            sub = ForzaTrackSubSection(self)

            # Generate per-subsection vertices (and possibly remapped indices)
            # If your Utilities.generate_vertices only returns vertices, drop the second assignment.
            verts, indices = Utilities.generate_vertices(base_vertices, sub.Indices)
            sub.Vertices = verts
            sub.Indices = indices

            # UV adjustments
            for v in sub.Vertices:
                v.texture0 *= sub.UVtile
                v.texture1 *= sub.UVtile
                v.texture0 += sub.UVoffset
                v.texture1 += sub.UVoffset
                v.texture0.y = 1.0 - v.texture0.y
                v.texture1.y = 1.0 - v.texture1.y

            # Convert tristrips to triangle list if needed
            if sub.IndexType == IndexType.TriStrip:
                sub.Indices = Utilities.generate_triangle_list(sub.Indices, sub.FaceCount)

            self.SubSections[j] = sub
