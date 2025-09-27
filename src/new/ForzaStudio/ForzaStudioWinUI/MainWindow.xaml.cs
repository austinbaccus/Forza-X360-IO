using ForzaStudioWinUI.Forza;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Threading.Tasks;
using Windows.Storage;
using Windows.Storage.Pickers;
using Windows.Storage.Provider;
using Windows.System;

namespace ForzaStudioWinUI
{
    public sealed partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();
            ExtendsContentIntoTitleBar = true;
            SetTitleBar(AppTitleBar);
        }

        private async void ImportFile(object sender, RoutedEventArgs e)
        {
            var filePicker = new FileOpenPicker();
            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);
            WinRT.Interop.InitializeWithWindow.Initialize(filePicker, hwnd);
            filePicker.FileTypeFilter.Add(".zip");
            var file = await filePicker.PickSingleFileAsync();
        }

        private async void ExportFile(object sender, RoutedEventArgs e)
        {
            var filePicker = new FileSavePicker();
            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);
            WinRT.Interop.InitializeWithWindow.Initialize(filePicker, hwnd);
            filePicker.FileTypeChoices.Add("Wavefront OBJ", new List<string>() { ".obj" });
            var file = await filePicker.PickSaveFileAsync();

            if (file != null)
            {
                CachedFileManager.DeferUpdates(file);
                await FileIO.WriteTextAsync(file, file.Name);
                await ExportGltf(file);
                FileUpdateStatus status = await CachedFileManager.CompleteUpdatesAsync(file);
            }
        }

        private void ImportForzaTrackBin(string archivePath, string fileName)
        {
            if (!fileName.EndsWith(".rmb.bin", StringComparison.InvariantCultureIgnoreCase))
            {
                throw new NotSupportedException();
            }
            UpdateStatus($"Importing {fileName}");
            using ForzaTrackBin forzaTrackBin = new ForzaTrackBin(archivePath, fileName);
            TreeNode treeNode = CreateNode(tvModels.Nodes, forzaTrackBin.FileName.Remove(forzaTrackBin.FileName.IndexOf('.')));
            ForzaTrackSection[] sections = forzaTrackBin.Sections;
            foreach (ForzaTrackSection forzaTrackSection in sections)
            {
                TreeNode treeNode2 = CreateNode(treeNode.Nodes, forzaTrackSection.Type);
                TreeNode treeNode3 = CreateNode(treeNode2.Nodes, forzaTrackSection.Name);
                ForzaTrackSubSection[] subSections = forzaTrackSection.SubSections;
                foreach (ForzaTrackSubSection forzaTrackSubSection in subSections)
                {
                    TreeNode treeNode4 = new TreeNode(forzaTrackSubSection.Name);
                    treeNode4.Tag = new ForzaMesh(forzaTrackBin.FileName + "_" + forzaTrackSection.Name + "_" + forzaTrackSubSection.Name, forzaTrackSubSection.Name, forzaTrackSubSection.Indices, forzaTrackSubSection.Vertices);
                    treeNode3.Nodes.Add(treeNode4);
                }
            }
        }

        private void ImportForzaTexture(string archivePath, string fileName)
        {
            if (!fileName.EndsWith(".xds", StringComparison.InvariantCultureIgnoreCase) && !fileName.EndsWith(".bix", StringComparison.InvariantCultureIgnoreCase) && !fileName.EndsWith("_b.bix", StringComparison.InvariantCultureIgnoreCase))
            {
                throw new NotSupportedException();
            }
            UpdateStatus($"Importing {fileName}");
            ForzaTexture forzaTexture = new ForzaTexture(archivePath, fileName);
            TreeNode treeNode = new TreeNode(forzaTexture.FileName);
            treeNode.Tag = forzaTexture;
            tvTextures.Nodes.Add(treeNode);
        }
        
        private void ExportWavefrontObj(bool selective)
        {
            List<ForzaMesh> modelMeshes = GetModelMeshes(tvModels.Nodes, selective);
            UpdateStatus("Building materials");
            Hashtable hashtable = new Hashtable();
            foreach (ForzaMesh item in modelMeshes)
            {
                hashtable[item.MaterialName] = 0;
            }
            if (hashtable.Count > 0)
            {
                using FileStream stream = new FileStream(saveFileDialog.FileName.Replace(".obj", "") + ".mtl", FileMode.Create, FileAccess.Write, FileShare.Read);
                using StreamWriter streamWriter = new StreamWriter(stream);
                foreach (DictionaryEntry item2 in hashtable)
                {
                    streamWriter.WriteLine("newmtl " + item2.Key);
                    Vector3 vector = Utilities.GetRandomColor(item2.Key.GetHashCode()).ToVector3();
                    streamWriter.WriteLine("kd {0} {1} {2}", vector.X, vector.Y, vector.Z);
                }
            }
            using (FileStream stream2 = new FileStream(saveFileDialog.FileName, FileMode.Create, FileAccess.Write, FileShare.Read))
            {
                using StreamWriter streamWriter2 = new StreamWriter(stream2);
                streamWriter2.WriteLine("# Extracted by Forza Studio 4.4 - Chipi's unofficial build- http://codeescape.com/" + Environment.NewLine);
                if (hashtable.Count > 0)
                {
                    streamWriter2.WriteLine("mtllib " + Path.GetFileName(saveFileDialog.FileName).Replace(".obj", "") + ".mtl");
                }
                int num = 0;
                foreach (ForzaMesh item3 in modelMeshes)
                {
                    UpdateStatus($"Extracting {item3.Name}");
                    streamWriter2.WriteLine("g {0}", item3.Name);
                    streamWriter2.WriteLine("# {0} vertices {1} faces", item3.VertexCount, item3.FaceCount);
                    ForzaVertex[] vertices = item3.Vertices;
                    for (int i = 0; i < vertices.Length; i++)
                    {
                        ForzaVertex forzaVertex = vertices[i];
                        streamWriter2.WriteLine("v {0} {1} {2}", forzaVertex.position.X.ToString(CultureInfo.InvariantCulture), forzaVertex.position.Y.ToString(CultureInfo.InvariantCulture), forzaVertex.position.Z.ToString(CultureInfo.InvariantCulture));
                    }
                    UVset = cmbExportUV.SelectedIndex;
                    switch (UVset)
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
                        streamWriter2.WriteLine("vn {0} {1} {2}", forzaVertex6.normal.X.ToString(CultureInfo.InvariantCulture), forzaVertex6.normal.Y.ToString(CultureInfo.InvariantCulture), forzaVertex6.normal.Z.ToString(CultureInfo.InvariantCulture));
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

        private async Task ExportGltf(StorageFile file)
        {

        }
    }
}
