using System;

namespace ForzaStudio;

public class ForzaCarSubSection
{
	public string Name;

	public EndianStream Stream;

	public ForzaCarSection Parent;

	public ForzaVertex[] Vertices;

	public int[] Indices;

	public int Lod;

	public IndexType IndexType;

	public int FaceCount;

	public int VertexCount;

	public float XUVOffset;

	public float XUVScale = 1f;

	public float YUVOffset;

	public float YUVScale = 1f;

	public float XUV2Offset;

	public float XUV2Scale = 1f;

	public float YUV2Offset;

	public float YUV2Scale = 1f;

	public static uint strippedCheck;

	public static int subSImax = 0;

	public ForzaCarSubSection(ForzaCarSection parentSection)
	{
		Parent = parentSection;
		Stream = parentSection.Stream;
		switch (parentSection.Parent.Version)
		{
		case ForzaVersion.Two:
			Stream.Position += 8L;
			break;
		case ForzaVersion.Three:
			Utilities.AssertEquals(Stream.ReadUInt32(), 2u);
			Stream.ReadByte();
			Utilities.AssertEquals(Stream.ReadUInt32(), 2u);
			break;
		case ForzaVersion.Four:
			Stream.Position += 5L;
			XUVOffset = Stream.ReadSingle();
			XUVScale = Stream.ReadSingle();
			YUVOffset = Stream.ReadSingle();
			YUVScale = Stream.ReadSingle();
			XUV2Offset = Stream.ReadSingle();
			XUV2Scale = Stream.ReadSingle();
			YUV2Offset = Stream.ReadSingle();
			YUV2Scale = Stream.ReadSingle();
			Stream.Position += 36L;
			break;
		case ForzaVersion.Horizon:
			Stream.Position += 5L;
			XUVOffset = Stream.ReadSingle();
			XUVScale = Stream.ReadSingle();
			YUVOffset = Stream.ReadSingle();
			YUVScale = Stream.ReadSingle();
			XUV2Offset = Stream.ReadSingle();
			XUV2Scale = Stream.ReadSingle();
			YUV2Offset = Stream.ReadSingle();
			YUV2Scale = Stream.ReadSingle();
			Stream.Position += 36L;
			break;
		default:
			throw new NotSupportedException();
		}
		Name = Stream.ReadASCII(Stream.ReadInt32());
		if (parentSection.Parent.Version == ForzaVersion.Two)
		{
			IndexType = (IndexType)Stream.ReadUInt32();
			Lod = Stream.ReadInt32();
		}
		else
		{
			Lod = Stream.ReadInt32();
			IndexType = (IndexType)Stream.ReadUInt32();
			Utilities.AssertEquals(Stream.ReadUInt32(), 0u);
			Utilities.AssertEquals(Stream.ReadUInt32(), 1u);
			Utilities.AssertEquals(Stream.ReadUInt32(), 0u);
			Utilities.AssertEquals(Stream.ReadUInt32(), 0u);
			Utilities.AssertEquals(Stream.ReadUInt32(), 0u);
			Utilities.AssertEquals(Stream.ReadUInt32(), 0u);
			Utilities.AssertEquals(Stream.ReadSingle(), 1f);
			Utilities.AssertEquals(Stream.ReadSingle(), 1f);
			Utilities.AssertEquals(Stream.ReadSingle(), 1f);
			Utilities.AssertEquals(Stream.ReadSingle(), 1f);
			Utilities.AssertEquals(Stream.ReadSingle(), 0f);
			Utilities.AssertEquals(Stream.ReadSingle(), 0f);
			Utilities.AssertEquals(Stream.ReadSingle(), 1f);
			Utilities.AssertEquals(Stream.ReadSingle(), 1f);
		}
		if (parentSection.Parent.Version == ForzaVersion.Two)
		{
			Utilities.AssertEquals(Stream.ReadUInt32(), 3u);
			Indices = Utilities.ReadIndices(Stream, Stream.ReadInt32(), Stream.ReadInt32());
			subSImax = 0;
			for (int i = 0; i < Indices.Length; i++)
			{
				if (Indices[i] > subSImax)
				{
					subSImax = Indices[i];
				}
			}
		}
		else if (parentSection.Parent.Version == ForzaVersion.Three || parentSection.Parent.Version == ForzaVersion.Four)
		{
			Utilities.AssertEquals(Stream.ReadUInt32(), 3u);
			Indices = Utilities.ReadIndices(Stream, Stream.ReadInt32(), Stream.ReadInt32());
			Stream.Position += 4L;
		}
		else if (parentSection.Parent.Version == ForzaVersion.Horizon)
		{
			Utilities.AssertEquals(Stream.ReadUInt32(), 4u);
			strippedCheck = Stream.ReadUInt32();
			if (strippedCheck == 2)
			{
				Stream.Position += 8L;
				Indices = Utilities.ReadIndices(Stream, 0, 0);
			}
			else
			{
				Indices = Utilities.ReadIndices(Stream, Stream.ReadInt32(), Stream.ReadInt32());
			}
			Stream.Position += 4L;
		}
		FaceCount = Utilities.CalculateFaceCount(Indices, IndexType);
		VertexCount = Utilities.CalculateVertexCount(Indices);
	}
}
