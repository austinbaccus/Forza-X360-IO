using Microsoft.Xna.Framework;

namespace ForzaStudio;

public class ForzaTrackSection
{
	public ForzaTrackBin Parent;

	public EndianStream Stream;

	public ForzaTrackSubSection[] SubSections;

	public string Name;

	public string Type;

	public Vector3 Offset;

	public ForzaTrackSection(ForzaTrackBin parent)
	{
		Parent = parent;
		Stream = parent.Stream;
		Utilities.AssertEquals(Stream.ReadUInt32(), 1u);
		new Vector3(Stream.ReadSingle(), Stream.ReadSingle(), Stream.ReadSingle());
		Utilities.AssertEquals(Stream.ReadSingle(), 0f);
		new Vector3(Stream.ReadSingle(), Stream.ReadSingle(), Stream.ReadSingle());
		Utilities.AssertEquals(Stream.ReadSingle(), 0f);
		new Vector3(Stream.ReadSingle(), Stream.ReadSingle(), Stream.ReadSingle());
		Utilities.AssertEquals(Stream.ReadSingle(), 0f);
		Utilities.AssertEquals(Stream.ReadUInt32(), 1u);
		Name = Stream.ReadASCII(Stream.ReadInt32()).ToLowerInvariant();
		string[] array = Name.Split('_');
		Type = array[0].ToLowerInvariant();
		Name = Name.Substring(Name.IndexOf("_") + 1);
		Utilities.AssertEquals(Stream.ReadUInt32(), 2u);
		uint num = Stream.ReadUInt32();
		uint size = Stream.ReadUInt32();
		ForzaVertex[] array2 = new ForzaVertex[num];
		for (int i = 0; i < num; i++)
		{
			ref ForzaVertex reference = ref array2[i];
			reference = new ForzaVertex(parent.Version, ForzaVertexType.Track, Stream, size);
		}
		Utilities.AssertEquals(Stream.ReadUInt32(), 1u);
		BoundingBox.FromVertices(array2);
		SubSections = new ForzaTrackSubSection[Stream.ReadUInt32()];
		for (int j = 0; j < SubSections.Length; j++)
		{
			ForzaTrackSubSection forzaTrackSubSection = new ForzaTrackSubSection(this);
			forzaTrackSubSection.Vertices = Utilities.GenerateVertices(array2, ref forzaTrackSubSection.Indices);
			for (int k = 0; k < forzaTrackSubSection.Vertices.Length; k++)
			{
				forzaTrackSubSection.Vertices[k].texture0 *= forzaTrackSubSection.UVtile;
				forzaTrackSubSection.Vertices[k].texture1 *= forzaTrackSubSection.UVtile;
				forzaTrackSubSection.Vertices[k].texture0 += forzaTrackSubSection.UVoffset;
				forzaTrackSubSection.Vertices[k].texture1 += forzaTrackSubSection.UVoffset;
				forzaTrackSubSection.Vertices[k].texture0.Y = 1f - forzaTrackSubSection.Vertices[k].texture0.Y;
				forzaTrackSubSection.Vertices[k].texture1.Y = 1f - forzaTrackSubSection.Vertices[k].texture1.Y;
			}
			if (forzaTrackSubSection.IndexType == IndexType.TriStrip)
			{
				forzaTrackSubSection.Indices = Utilities.GenerateTriangleList(forzaTrackSubSection.Indices, forzaTrackSubSection.FaceCount);
			}
			SubSections[j] = forzaTrackSubSection;
		}
	}
}
