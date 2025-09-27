using System;
using Microsoft.Xna.Framework.Graphics;

namespace ForzaStudio;

public class ForzaMesh : IDisposable
{
	public string Name;

	public string MaterialName;

	public int[] Indices;

	public ForzaVertex[] Vertices;

	public int FaceCount => Indices.Length / 3;

	public int VertexCount => Vertices.Length;

	public ForzaMesh(string name, string materialName, int[] indices, ForzaVertex[] vertices)
	{
		Name = name;
		MaterialName = materialName;
		Indices = indices;
		Vertices = vertices;
	}

	~ForzaMesh()
	{
		Dispose();
	}

	public void Draw(ref GraphicsDevice device)
	{
		device.VertexDeclaration = new VertexDeclaration(device, ForzaVertex.VertexElements);
		device.DrawUserIndexedPrimitives(PrimitiveType.TriangleList, Vertices, 0, Vertices.Length, Indices, 0, FaceCount);
	}

	public void Dispose()
	{
		Name = null;
		MaterialName = null;
		Indices = null;
		Vertices = null;
	}
}
