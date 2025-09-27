using System;
using Microsoft.Xna.Framework;

namespace ForzaStudio;

public struct BoundingBox
{
	public float MinX;

	public float MaxX;

	public float MinY;

	public float MaxY;

	public float MinZ;

	public float MaxZ;

	public float XRange => MaxX - MinX;

	public float YRange => MaxY - MinY;

	public float ZRange => MaxZ - MaxX;

	public Vector3 Min => new Vector3(MinX, MinY, MinZ);

	public Vector3 Max => new Vector3(MaxX, MaxY, MaxZ);

	public Vector3 Range => new Vector3(MaxX - MinX, MaxY - MinY, MaxZ - MinZ);

	public static BoundingBox FromVertices(ForzaVertex[] vertices)
	{
		BoundingBox result = default(BoundingBox);
		if (vertices != null && vertices.Length > 0)
		{
			for (int i = 0; i < vertices.Length; i++)
			{
				ForzaVertex forzaVertex = vertices[i];
				result.MinX = Math.Min(forzaVertex.position.X, result.MinX);
				result.MaxX = Math.Max(forzaVertex.position.X, result.MaxX);
				result.MinY = Math.Min(forzaVertex.position.Y, result.MinY);
				result.MaxY = Math.Max(forzaVertex.position.Y, result.MaxY);
				result.MinZ = Math.Min(forzaVertex.position.Z, result.MinZ);
				result.MaxZ = Math.Max(forzaVertex.position.Z, result.MaxZ);
			}
		}
		return result;
	}
}
