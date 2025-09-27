using System;

namespace Forza
{
    public class ForzaTrackSubSection
    {
        public ForzaTrackSection Parent;

        public EndianStream Stream;

        public string Name;

        public uint Lod;

        public IndexType IndexType;

        public int[] Indices;

        public ForzaVertex[] Vertices;

        public int VertexCount;

        public int FaceCount;

        public Vector3 Offset;

        public Vector2 UVoffset;

        public Vector2 UVtile;

        public ForzaTrackSubSection(ForzaTrackSection parent)
        {
            Parent = parent;
            Stream = parent.Stream;
            Utilities.AssertEquals(Stream.ReadUInt32(), 1u);
            Utilities.AssertEquals(Stream.ReadUInt32(), 2u);
            Name = Stream.ReadASCII(Stream.ReadInt32()).ToLowerInvariant();
            Lod = Stream.ReadUInt32();
            IndexType = (IndexType)Stream.ReadUInt32();
            if (IndexType != IndexType.TriList && IndexType != IndexType.TriStrip)
            {
                throw new Exception("analyze this!");
            }
            uint num = Stream.ReadUInt32();
            Utilities.AssertEquals(Stream.ReadUInt32(), 1u);
            Utilities.AssertEquals(Stream.ReadUInt32(), 0u);
            Utilities.AssertEquals(Stream.ReadUInt32(), 0u);
            Utilities.AssertEquals(Stream.ReadUInt32(), 0u);
            Utilities.AssertEquals(Stream.ReadUInt32(), 0u);
            Utilities.AssertEquals(Stream.ReadSingle(), 1f);
            Utilities.AssertEquals(Stream.ReadSingle(), 1f);
            Utilities.AssertEquals(Stream.ReadSingle(), 1f);
            Utilities.AssertEquals(Stream.ReadSingle(), 1f);
            UVoffset = new Vector2(Stream.ReadSingle(), Stream.ReadSingle());
            UVtile = new Vector2(Stream.ReadSingle(), Stream.ReadSingle());
            Utilities.AssertEquals(Stream.ReadUInt32(), 3u);
            Indices = Utilities.ReadIndices(Stream, Stream.ReadInt32(), Stream.ReadInt32());
            num = Stream.ReadUInt32();
            if (num != 0 && num != 1 && num != 2 && num != 5)
            {
                throw new Exception("analyze this!");
            }
            VertexCount = Utilities.CalculateVertexCount(Indices);
            FaceCount = Utilities.CalculateFaceCount(Indices, IndexType);
        }
    }
}
