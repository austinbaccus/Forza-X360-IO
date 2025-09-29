using ForzaStudioCLI.Forza;
using System.Collections;
using System.Globalization;
using System.Numerics;

namespace Forza
{
    class Program
    {
        public static List<ForzaTexture> Textures = new();
        public static List<ForzaMesh> Meshes = new();
        public static HashSet<uint> Formats = new();

        static void Main(string[] args)
        {
            //ImportForzaTexture(@"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\_decompressed\Amalfi\bin", "_0x00000A53.bix");
            //Textures[0].GetImage().Save("test.bmp", System.Drawing.Imaging.ImageFormat.Bmp);
            

            if (args.Length == 0)
            {
                Console.WriteLine("Usage: FilePathExample <file-path>");
                return;
            }

            UnpackZip(args[0]);
            //UnpackZip(@"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\MapleValley\bin.zip");

            //ExportWavefrontObj();
            for (int i = 0; i < Textures.Count; i++)
            {
                if (Formats.Add(Textures[i].GetFormat()))
                {
                    Console.WriteLine($"This image has a new format value! {Textures[i].FileName} {Textures[i].GetFormat()}");
                }
            }

            foreach (uint i in Formats)
            {
                Console.WriteLine(i);
            }
            Console.WriteLine();

            //ForzaTexture a5e_a = Textures[1423];
            //a5e_a.GetImage();
            //Textures[1423].GetImage().Save("test.bmp", System.Drawing.Imaging.ImageFormat.Bmp);
        }

        private static void UnpackZip(string archivePath)
        {
            using ForzaArchive forzaArchive = new ForzaArchive(archivePath);
            foreach (ZipFile file in forzaArchive.Files)
            {
                Console.WriteLine($"Importing {file.FileName}");
                try
                {
                    if (file.FileName.EndsWith(".carbin", StringComparison.InvariantCultureIgnoreCase))
                    {
                        ImportForzaCarBin(archivePath, file.FileName);
                    }
                    else if (file.FileName.EndsWith(".rmb.bin", StringComparison.InvariantCultureIgnoreCase))
                    {
                        ImportForzaTrackBin(archivePath, file.FileName);
                    }
                    else if (file.FileName.EndsWith(".xds", StringComparison.InvariantCultureIgnoreCase) || (file.FileName.EndsWith(".bix", StringComparison.InvariantCultureIgnoreCase) && !file.FileName.EndsWith("_b.bix", StringComparison.InvariantCultureIgnoreCase)))
                    {
                        ImportForzaTexture(archivePath, file.FileName);
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Failed to import {file.FileName}");
                }
            }
        }

        private static void ImportForzaTrackBin(string archivePath, string fileName)
        {
            if (!fileName.EndsWith(".rmb.bin", StringComparison.InvariantCultureIgnoreCase))
            {
                throw new NotSupportedException();
            }
            using ForzaTrackBin forzaTrackBin = new ForzaTrackBin(archivePath, fileName);
            ForzaTrackSection[] sections = forzaTrackBin.Sections;
            foreach (ForzaTrackSection forzaTrackSection in sections)
            {
                ForzaTrackSubSection[] subSections = forzaTrackSection.SubSections;
                foreach (ForzaTrackSubSection forzaTrackSubSection in subSections)
                {
                    string meshName = forzaTrackBin.FileName + "_" + forzaTrackSection.Name + "_" + forzaTrackSubSection.Name;
                    Meshes.Add(new ForzaMesh(meshName, forzaTrackSubSection.Name, forzaTrackSubSection.Indices, forzaTrackSubSection.Vertices));
                }
            }
        }

        private static void ImportForzaTexture(string archivePath, string fileName)
        {
            if (!fileName.EndsWith(".xds", StringComparison.InvariantCultureIgnoreCase) && !fileName.EndsWith(".bix", StringComparison.InvariantCultureIgnoreCase) && !fileName.EndsWith("_b.bix", StringComparison.InvariantCultureIgnoreCase))
            {
                throw new NotSupportedException();
            }
            ForzaTexture forzaTexture = new ForzaTexture(archivePath, fileName);
            Textures.Add(forzaTexture);
        }

        private static void ImportForzaCarBin(string archivePath, string fileName)
        {
            if (!fileName.EndsWith(".carbin", StringComparison.InvariantCultureIgnoreCase))
            {
                throw new NotSupportedException();
            }
            using ForzaCarBin forzaCarBin = new ForzaCarBin(archivePath, fileName);
            ForzaCarSection[] sections = forzaCarBin.Sections;
            foreach (ForzaCarSection forzaCarSection in sections)
            {
                ForzaCarSubSection[] subSections = forzaCarSection.SubSections;
            }
        }

        private static void ExportWavefrontObj()
        {
            string filename = "test";

            Hashtable hashtable = new Hashtable();
            foreach (ForzaMesh item in Meshes)
            {
                hashtable[item.MaterialName] = 0;
            }

            // .mtl
            if (hashtable.Count > 0)
            {
                using FileStream stream = new FileStream($"{filename}.mtl", FileMode.Create, FileAccess.Write, FileShare.Read);
                using StreamWriter streamWriter = new StreamWriter(stream);
                foreach (DictionaryEntry item2 in hashtable)
                {
                    streamWriter.WriteLine("newmtl " + item2.Key);
                    //Vector3 vector = Utilities.GetRandomColor(item2.Key.GetHashCode()).ToVector3();
                    //streamWriter.WriteLine("kd {0} {1} {2}", vector.X, vector.Y, vector.Z);
                    streamWriter.WriteLine("kd {0} {1} {2}", 0, 0, 0);
                }
            }

            // .obj
            using (FileStream stream2 = new FileStream("test.obj", FileMode.Create, FileAccess.Write, FileShare.Read))
            {
                using StreamWriter streamWriter2 = new StreamWriter(stream2);
                streamWriter2.WriteLine("# Extracted by Forza Studio 5.0" + Environment.NewLine);
                if (hashtable.Count > 0)
                {
                    streamWriter2.WriteLine("mtllib " + $"{filename}.mtl");
                }
                int num = 0;

                foreach (ForzaMesh item3 in Meshes)
                {
                    streamWriter2.WriteLine("g {0}", item3.Name);
                    streamWriter2.WriteLine("# {0} vertices {1} faces", item3.VertexCount, item3.FaceCount);
                    ForzaVertex[] vertices = item3.Vertices;
                    for (int i = 0; i < vertices.Length; i++)
                    {
                        ForzaVertex forzaVertex = vertices[i];
                        streamWriter2.WriteLine("v {0} {1} {2}", forzaVertex.position.X.ToString(CultureInfo.InvariantCulture), forzaVertex.position.Y.ToString(CultureInfo.InvariantCulture), forzaVertex.position.Z.ToString(CultureInfo.InvariantCulture));
                    }

                    // You know how FS4.4 lets you choose which UV set to choose from? This is where it manifests in the code.
                    int uvSet = 0;
                    switch (uvSet)
                    {
                        case 0:
                            {
                                ForzaVertex[] vertices4 = item3.Vertices;
                                for (int l = 0; l < vertices4.Length; l++)
                                {
                                    ForzaVertex forzaVertex4 = vertices4[l];
                                    streamWriter2.WriteLine("vt {0} {1}", forzaVertex4.texture0.X.ToString(CultureInfo.InvariantCulture), forzaVertex4.texture0.Y.ToString(CultureInfo.InvariantCulture));
                                }
                                break;
                            }
                        case 1:
                            {
                                ForzaVertex[] vertices5 = item3.Vertices;
                                for (int m = 0; m < vertices5.Length; m++)
                                {
                                    ForzaVertex forzaVertex5 = vertices5[m];
                                    streamWriter2.WriteLine("vt {0} {1}", forzaVertex5.texture1.X.ToString(CultureInfo.InvariantCulture), forzaVertex5.texture1.Y.ToString(CultureInfo.InvariantCulture));
                                }
                                break;
                            }
                        case 2:
                            {
                                ForzaVertex[] vertices2 = item3.Vertices;
                                for (int j = 0; j < vertices2.Length; j++)
                                {
                                    ForzaVertex forzaVertex2 = vertices2[j];
                                    streamWriter2.WriteLine("vt {0} {1}", forzaVertex2.texture0.X.ToString(CultureInfo.InvariantCulture), forzaVertex2.texture0.Y.ToString(CultureInfo.InvariantCulture));
                                }
                                ForzaVertex[] vertices3 = item3.Vertices;
                                for (int k = 0; k < vertices3.Length; k++)
                                {
                                    ForzaVertex forzaVertex3 = vertices3[k];
                                    streamWriter2.WriteLine("#uv2 {0} {1} ", forzaVertex3.texture1.X.ToString(CultureInfo.InvariantCulture), forzaVertex3.texture1.Y.ToString(CultureInfo.InvariantCulture));
                                }
                                break;
                            }
                    }
                    ForzaVertex[] vertices6 = item3.Vertices;
                    for (int n = 0; n < vertices6.Length; n++)
                    {
                        ForzaVertex forzaVertex6 = vertices6[n];
                        // forzaVertex6.normal was null.
                        if (forzaVertex6.normal == null)
                        {
                            streamWriter2.WriteLine("vn 0 0 0");
                        }
                        else
                        {
                            streamWriter2.WriteLine("vn {0} {1} {2}", forzaVertex6.normal.X.ToString(CultureInfo.InvariantCulture), forzaVertex6.normal.Y.ToString(CultureInfo.InvariantCulture), forzaVertex6.normal.Z.ToString(CultureInfo.InvariantCulture));
                        }
                    }
                    streamWriter2.WriteLine("usemtl {0}", item3.MaterialName);
                    for (int num2 = 0; num2 < item3.Indices.Length; num2 += 3)
                    {
                        int num3 = item3.Indices[num2] + 1;
                        int num4 = item3.Indices[num2 + 1] + 1;
                        int num5 = item3.Indices[num2 + 2] + 1;
                        if (num3 != num4 && num4 != num5 && num3 != num5)
                        {
                            streamWriter2.WriteLine("f {0}/{0}/{0} {1}/{1}/{1} {2}/{2}/{2}", num + item3.Indices[num2] + 1, num + item3.Indices[num2 + 1] + 1, num + item3.Indices[num2 + 2] + 1);
                        }
                    }
                    num += item3.Vertices.Length;
                }
            }
        }
    }
}
