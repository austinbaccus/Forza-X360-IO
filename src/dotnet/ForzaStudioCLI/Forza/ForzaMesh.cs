using SharpDX.Direct3D9;
using System;

<<<<<<< HEAD:src/dotnet/ForzaStudioCLI/Forza/ForzaMesh.cs
namespace Forza
=======
namespace ForzaStudioWinUI.Forza
>>>>>>> a29b15f28bd03977571690db830a7d6ffe29cb82:src/new/ForzaStudio/ForzaStudioWinUI/Forza/ForzaMesh.cs
{
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

        public void Dispose()
        {
            Name = null;
            MaterialName = null;
            Indices = null;
            Vertices = null;
        }
    }
}
