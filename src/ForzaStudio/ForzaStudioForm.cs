using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;

namespace ForzaStudio;

public class ForzaStudioForm : Form
{
	public Image SelectedTexture;

	public RenderScene Scene;

	public int SelectedVertexCount;

	public int SelectedFaceCount;

	public int UVset;

	private IContainer components;

	private StatusStrip statusStrip1;

	private MenuStrip mnuMain;

	private ToolStripMenuItem mnuFile;

	private ToolStripMenuItem mnuAbout;

	private SplitContainer splitContainer1;

	private TreeView tvModels;

	private TabControl tabForzaObjects;

	private TabPage tabModels;

	private TabPage tabTextures;

	private TreeView tvTextures;

	private ToolStripMenuItem mnuImport;

	private ToolStripMenuItem mnuExit;

	private Panel pnlViewport;

	private ContextMenuStrip ctxViewportMenu;

	private ToolStripMenuItem mnuShowWireframe;

	private ContextMenuStrip ctxModelTreeMenu;

	private ContextMenuStrip ctxTextureTreeMenu;

	private ToolStripMenuItem mnuExtractAllModels;

	private ToolStripMenuItem mnuExtractCheckedModels;

	private ToolStripMenuItem mnuExtractAllTextures;

	private ToolStripMenuItem mnuExtractSelectedTextures;

	private ToolStripMenuItem mnuUnpackArchive;

	private Panel pnlTextureDisplay;

	private ContextMenuStrip ctxTextureMenu;

	private ToolStripMenuItem mnuShowTextureAlpha;

	private ToolStripMenuItem mnuSaveTextureAs;

	private ToolStripMenuItem mnuUtilities;

	private ToolStripStatusLabel lblStatus;

	private ToolStripMenuItem mnuExportObj;

	private ToolStripComboBox cmbViewportSpeed;

	private ToolStripStatusLabel lblInformation;

	private ToolStripSeparator toolStripSeparator1;

	private ToolStripComboBox cmbExportUV;

	private ToolStripMenuItem mnuCreateLog;

	public bool CreateLog { get; set; }

	public ForzaStudioForm()
	{
		InitializeComponent();
		BindCameraSpeeds();
		BindUVset();
		SetDoubleBuffered(pnlTextureDisplay);
		Scene = new RenderScene(ref tvModels, ref pnlViewport);
	}

	private void tabForzaObjects_Selecting(object sender, TabControlCancelEventArgs e)
	{
		bool flag = e.TabPageIndex == 0;
		pnlViewport.Visible = flag;
		pnlTextureDisplay.Visible = !flag;
		pnlTextureDisplay.BackColor = System.Drawing.Color.White;
	}

	private void ForzaStudioForm_Shown(object sender, EventArgs e)
	{
		while (!base.IsDisposed)
		{
			UpdateScene(forceUpdate: false);
			UpdateStatus();
			Thread.Sleep(1);
		}
	}

	private void mnuImport_Click(object sender, EventArgs e)
	{
		using (OpenFileDialog openFileDialog = new OpenFileDialog())
		{
			openFileDialog.Multiselect = false;
			openFileDialog.Filter = "All Forza Files|*.zip;*.carbin;*.rmb.bin;*.xds;*.bix|Forza Archive (.zip)|*.zip|Forza Car Object (.carbin)|*.carbin|Forza Track Object (.rmb.bin)|*.rmb.bin|Forza Texture (.xds, .bix)|*.xds;*.bix";
			if (openFileDialog.ShowDialog() == DialogResult.OK)
			{
				tvModels.Nodes.Clear();
				tvTextures.Nodes.Clear();
				ImportFile(openFileDialog.FileName);
				MessageBox.Show("Import Complete!", "Finished", MessageBoxButtons.OK, MessageBoxIcon.Asterisk);
			}
		}
		tvModels.Sort();
		tvTextures.Sort();
		pnlTextureDisplay.Invalidate();
		pnlViewport.Invalidate();
		UpdateStatus();
	}

	private void mnuExtractZip_Click(object sender, EventArgs e)
	{
		try
		{
			using OpenFileDialog openFileDialog = new OpenFileDialog();
			openFileDialog.Filter = "Forza Archive (.zip)|*.zip";
			if (openFileDialog.ShowDialog() == DialogResult.OK)
			{
				using FolderBrowserDialog folderBrowserDialog = new FolderBrowserDialog();
				if (folderBrowserDialog.ShowDialog() == DialogResult.OK)
				{
					using (ForzaArchive forzaArchive = new ForzaArchive(openFileDialog.FileName))
					{
						foreach (ZipFile file in forzaArchive.Files)
						{
							try
							{
								UpdateStatus($"Extracting {file.FileName}");
								string text = folderBrowserDialog.SelectedPath + "\\" + file.FileName;
								Directory.CreateDirectory(Path.GetDirectoryName(text));
								file.SaveAs(text);
							}
							catch (Exception)
							{
								MessageBox.Show($"Failed to extract {file.FileName} from {Path.GetFileName(openFileDialog.FileName)}.", "Forza Studio Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
							}
						}
					}
					MessageBox.Show("Extraction Complete!", "Finished", MessageBoxButtons.OK, MessageBoxIcon.Asterisk);
				}
			}
		}
		catch (Exception ex2)
		{
			MessageBox.Show(ex2.ToString(), "Forza Studio Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
		}
		UpdateStatus();
	}

	private void mnuExit_Click(object sender, EventArgs e)
	{
		Close();
	}

	private void mnuAbout_Click(object sender, EventArgs e)
	{
		StringBuilder stringBuilder = new StringBuilder();
		stringBuilder.AppendLine("Developed By:\tMike Davis");
		stringBuilder.AppendLine("Website:\t\thttp://codeescape.com/");
		stringBuilder.AppendLine("Research:\thttp://forum.xentax.com/");
		MessageBox.Show(stringBuilder.ToString(), "About Forza Studio", MessageBoxButtons.OK, MessageBoxIcon.Asterisk);
	}

	private void ctxTextureMenu_Opening(object sender, CancelEventArgs e)
	{
		e.Cancel = tvTextures.Nodes.Count == 0;
	}

	private void ctxTextureTreeMenu_Opening(object sender, CancelEventArgs e)
	{
		e.Cancel = tvTextures.Nodes.Count == 0;
	}

	private void tvTextures_AfterSelect(object sender, TreeViewEventArgs e)
	{
		try
		{
			if (SelectedTexture != null)
			{
				SelectedTexture.Dispose();
			}
			SelectedTexture = ((ForzaTexture)e.Node.Tag).GetImage();
		}
		catch (Exception)
		{
		}
		pnlTextureDisplay.Invalidate();
	}

	private void pnlTextureDisplay_Paint(object sender, PaintEventArgs e)
	{
		if (tvTextures.SelectedNode == null || SelectedTexture == null)
		{
			return;
		}
		try
		{
			int num = Math.Min(e.ClipRectangle.Width, SelectedTexture.Width);
			int num2 = Math.Min(e.ClipRectangle.Height, SelectedTexture.Height);
			double num3 = Math.Abs(Math.Max((double)SelectedTexture.Width / (double)num, (double)SelectedTexture.Height / (double)num2));
			num = (int)((double)SelectedTexture.Width / num3);
			num2 = (int)((double)SelectedTexture.Height / num3);
			int num4 = (int)((double)e.ClipRectangle.Width - (double)num) / 2;
			int num5 = (int)((double)e.ClipRectangle.Height - (double)num2) / 2;
			if (mnuShowTextureAlpha.Checked)
			{
				e.Graphics.DrawImage(SelectedTexture, num4, num5, num, num2);
				return;
			}
			using MemoryStream stream = new MemoryStream();
			SelectedTexture.Save(stream, ImageFormat.Bmp);
			e.Graphics.DrawImage(Image.FromStream(stream), num4, num5, num, num2);
		}
		catch (Exception)
		{
		}
	}

	private void pnlTextureDisplay_Resize(object sender, EventArgs e)
	{
		pnlTextureDisplay.Invalidate();
	}

	private void mnuShowTextureAlpha_CheckedChanged(object sender, EventArgs e)
	{
		pnlTextureDisplay.Invalidate();
	}

	private void mnuSaveTextureAs_Click(object sender, EventArgs e)
	{
		try
		{
			using SaveFileDialog saveFileDialog = new SaveFileDialog();
			saveFileDialog.Filter = "Bitmap (*.bmp)|*.bmp|PNG (*.png)|*.png|JPEG (*.jpg)|*.jpg";
			if (saveFileDialog.ShowDialog() == DialogResult.OK)
			{
				ImageFormat format = Path.GetExtension(saveFileDialog.FileName.ToLowerInvariant()) switch
				{
					".bmp" => ImageFormat.Bmp, 
					".png" => ImageFormat.Png, 
					".jpg" => ImageFormat.Jpeg, 
					".jpeg" => ImageFormat.Jpeg, 
					_ => throw new NotSupportedException(), 
				};
				using Image image = ((ForzaTexture)tvTextures.SelectedNode.Tag).GetImage();
				image.Save(saveFileDialog.FileName, format);
				return;
			}
		}
		catch (Exception)
		{
		}
	}

	private void mnuExtractAllTextures_Click(object sender, EventArgs e)
	{
		using FolderBrowserDialog folderBrowserDialog = new FolderBrowserDialog();
		if (folderBrowserDialog.ShowDialog() != DialogResult.OK)
		{
			return;
		}
		foreach (TreeNode node in tvTextures.Nodes)
		{
			ForzaTexture forzaTexture = node.Tag as ForzaTexture;
			UpdateStatus($"Extracting {forzaTexture.FileName}");
			using Image image = forzaTexture.GetImage();
			image.Save(folderBrowserDialog.SelectedPath + "\\" + forzaTexture.FileName + ".bmp", ImageFormat.Bmp);
		}
		MessageBox.Show("Extraction Complete!", "Finished", MessageBoxButtons.OK, MessageBoxIcon.Asterisk);
	}

	private void mnuExtractCheckedTextures_Click(object sender, EventArgs e)
	{
		using FolderBrowserDialog folderBrowserDialog = new FolderBrowserDialog();
		if (folderBrowserDialog.ShowDialog() != DialogResult.OK)
		{
			return;
		}
		foreach (TreeNode node in tvTextures.Nodes)
		{
			if (node.Checked)
			{
				ForzaTexture forzaTexture = node.Tag as ForzaTexture;
				UpdateStatus($"Extracting {forzaTexture.FileName}");
				using Image image = forzaTexture.GetImage();
				image.Save(folderBrowserDialog.SelectedPath + "\\" + forzaTexture.FileName + ".bmp", ImageFormat.Bmp);
			}
		}
		MessageBox.Show("Extraction Complete!", "Finished", MessageBoxButtons.OK, MessageBoxIcon.Asterisk);
	}

	private void tvModels_AfterCheck(object sender, TreeViewEventArgs e)
	{
		tvModels.AfterCheck -= tvModels_AfterCheck;
		SetChildrenCheckedStatus(e.Node, e.Node.Checked);
		tvModels.AfterCheck += tvModels_AfterCheck;
		pnlViewport.Invalidate();
		SelectedVertexCount = GetSelectedVertexCount(tvModels.Nodes);
		SelectedFaceCount = GetSelectedFaceCount(tvModels.Nodes);
		Application.DoEvents();
	}

	private void mnuShowWireframe_Click(object sender, EventArgs e)
	{
		RenderScene scene = Scene;
		scene.ShowWireframe = !scene.ShowWireframe;
		Scene.Update(forceRedraw: true);
	}

	private void mnuExportObj_Click(object sender, EventArgs e)
	{
		ExportWavefrontObj(selective: true);
	}

	private void pnlViewport_Resize(object sender, EventArgs e)
	{
		Scene.ResetGraphicsDevice();
	}

	private void pnlViewport_Paint(object sender, PaintEventArgs e)
	{
		Scene.Update(forceRedraw: true);
	}

	private void ctxModelMenu_Opening(object sender, CancelEventArgs e)
	{
		e.Cancel = tvModels.Nodes.Count == 0;
	}

	private void ctxViewportMenu_Opening(object sender, CancelEventArgs e)
	{
		e.Cancel = tvModels.Nodes.Count == 0;
	}

	private void mnuExtractCheckedModels_Click(object sender, EventArgs e)
	{
		ExportWavefrontObj(selective: true);
	}

	private void mnuExtractAllModels_Click(object sender, EventArgs e)
	{
		ExportWavefrontObj(selective: false);
	}

	private void Form1_MouseWheel(object sender, MouseEventArgs e)
	{
		if (e.Delta < 0)
		{
			Scene.Camera.ApplyZoomForce(0.02f);
		}
		else if (e.Delta > 0)
		{
			Scene.Camera.ApplyZoomForce(-0.02f);
		}
	}

	private void UpdateScene(bool forceUpdate)
	{
		try
		{
			Scene.Camera.SpeedScale = ((ComboBoxItem<float>)cmbViewportSpeed.SelectedItem).Value;
			Mouse.GetState();
			KeyboardState keyboardState = Keyboard.GetState();
			GamePad.GetState(PlayerIndex.One);
			if (keyboardState.IsKeyDown(Microsoft.Xna.Framework.Input.Keys.W))
			{
				Scene.Camera.ApplyForce(Scene.Camera.ForwardDirection);
			}
			if (keyboardState.IsKeyDown(Microsoft.Xna.Framework.Input.Keys.A))
			{
				Scene.Camera.ApplyForce(-Scene.Camera.HorizontalDirection);
			}
			if (keyboardState.IsKeyDown(Microsoft.Xna.Framework.Input.Keys.S))
			{
				Scene.Camera.ApplyForce(-Scene.Camera.ForwardDirection);
			}
			if (keyboardState.IsKeyDown(Microsoft.Xna.Framework.Input.Keys.D))
			{
				Scene.Camera.ApplyForce(Scene.Camera.HorizontalDirection);
			}
			if (keyboardState.IsKeyDown(Microsoft.Xna.Framework.Input.Keys.Q))
			{
				Scene.Camera.ApplyForce(new Vector3(0f, -1f, 0f));
			}
			if (keyboardState.IsKeyDown(Microsoft.Xna.Framework.Input.Keys.E))
			{
				Scene.Camera.ApplyForce(new Vector3(0f, 1f, 0f));
			}
			if (keyboardState.IsKeyDown(Microsoft.Xna.Framework.Input.Keys.Up))
			{
				Scene.Camera.ApplyLookForce(new Vector2(0f, 0.1f));
			}
			if (keyboardState.IsKeyDown(Microsoft.Xna.Framework.Input.Keys.Left))
			{
				Scene.Camera.ApplyLookForce(new Vector2(-0.1f, 0f));
			}
			if (keyboardState.IsKeyDown(Microsoft.Xna.Framework.Input.Keys.Down))
			{
				Scene.Camera.ApplyLookForce(new Vector2(0f, -0.1f));
			}
			if (keyboardState.IsKeyDown(Microsoft.Xna.Framework.Input.Keys.Right))
			{
				Scene.Camera.ApplyLookForce(new Vector2(0.1f, 0f));
			}
			Scene.Update();
		}
		catch (DeviceLostException)
		{
			Scene.ResetGraphicsDevice();
		}
	}

	public static void SetDoubleBuffered(Control control)
	{
		typeof(Control).InvokeMember("DoubleBuffered", BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.SetProperty, null, control, new object[1] { true });
	}

	private void ImportFile(string fileName)
	{
		try
		{
			SelectedVertexCount = 0;
			SelectedFaceCount = 0;
			if (SelectedTexture != null)
			{
				SelectedTexture.Dispose();
				SelectedTexture = null;
			}
			if (fileName.EndsWith(".zip", StringComparison.InvariantCultureIgnoreCase))
			{
				using ForzaArchive forzaArchive = new ForzaArchive(fileName);
				foreach (ZipFile file in forzaArchive.Files)
				{
					try
					{
						string fileName2 = file.FileName;
						if (fileName2.EndsWith(".carbin", StringComparison.InvariantCultureIgnoreCase))
						{
							ImportForzaCarBin(fileName, fileName2);
						}
						else if (fileName2.EndsWith(".rmb.bin", StringComparison.InvariantCultureIgnoreCase))
						{
							ImportForzaTrackBin(fileName, fileName2);
						}
						else if (fileName2.EndsWith(".xds", StringComparison.InvariantCultureIgnoreCase) || (fileName2.EndsWith(".bix", StringComparison.InvariantCultureIgnoreCase) && !fileName2.EndsWith("_b.bix", StringComparison.InvariantCultureIgnoreCase)))
						{
							ImportForzaTexture(fileName, fileName2);
						}
					}
					catch (Exception ex)
					{
						MessageBox.Show($"Failed to import {fileName}\n\n{ex.ToString()}", "Forza Studio Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					}
					Application.DoEvents();
				}
			}
			else if (fileName.EndsWith(".carbin", StringComparison.InvariantCultureIgnoreCase))
			{
				ImportForzaCarBin(null, fileName);
			}
			else if (fileName.EndsWith(".rmb.bin", StringComparison.InvariantCultureIgnoreCase))
			{
				ImportForzaTrackBin(null, fileName);
			}
			else if (fileName.EndsWith(".xds", StringComparison.InvariantCultureIgnoreCase) || (fileName.EndsWith(".bix", StringComparison.InvariantCultureIgnoreCase) && !fileName.EndsWith("_b.bix", StringComparison.InvariantCultureIgnoreCase)))
			{
				ImportForzaTexture(null, fileName);
			}
		}
		catch (Exception ex2)
		{
			MessageBox.Show($"Failed to import {fileName}\n\n{ex2.ToString()}", "Forza Studio Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
		}
		Application.DoEvents();
	}

	private void ImportForzaCarBin(string archivePath, string fileName)
	{
		if (!fileName.EndsWith(".carbin", StringComparison.InvariantCultureIgnoreCase))
		{
			throw new NotSupportedException();
		}
		UpdateStatus($"Importing {fileName}");
		using ForzaCarBin forzaCarBin = new ForzaCarBin(archivePath, fileName);
		TreeNode treeNode = CreateNode(tvModels.Nodes, forzaCarBin.FileName);
		ForzaCarSection[] sections = forzaCarBin.Sections;
		foreach (ForzaCarSection forzaCarSection in sections)
		{
			ForzaCarSubSection[] subSections = forzaCarSection.SubSections;
			foreach (ForzaCarSubSection forzaCarSubSection in subSections)
			{
				TreeNode treeNode2 = CreateNode(treeNode.Nodes, "LOD" + forzaCarSubSection.Lod);
				TreeNode treeNode3 = CreateNode(treeNode2.Nodes, forzaCarSection.Name);
				TreeNode treeNode4 = new TreeNode(forzaCarSubSection.Name);
				treeNode4.Tag = new ForzaMesh(forzaCarSection.Name + "_" + forzaCarSubSection.Name, forzaCarSubSection.Name, forzaCarSubSection.Indices, forzaCarSubSection.Vertices);
				treeNode3.Nodes.Add(treeNode4);
			}
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

	private TreeNode CreateNode(TreeNodeCollection nodes, string name)
	{
		TreeNode treeNode = nodes[name];
		if (treeNode == null)
		{
			treeNode = new TreeNode(name);
			treeNode.Name = name;
			nodes.Add(treeNode);
		}
		return treeNode;
	}

	private void SetChildrenCheckedStatus(TreeNode node, bool isChecked)
	{
		foreach (TreeNode node2 in node.Nodes)
		{
			node2.Checked = isChecked;
			SetChildrenCheckedStatus(node2, isChecked);
		}
	}

	private void ExportWavefrontObj(bool selective)
	{
		using (SaveFileDialog saveFileDialog = new SaveFileDialog())
		{
			saveFileDialog.Filter = "Wavefront OBJ (*.obj)|*.obj";
			if (saveFileDialog.ShowDialog() == DialogResult.OK)
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
				if (CreateLog)
				{
					using FileStream stream3 = new FileStream(saveFileDialog.FileName.Replace(".obj", "") + ".log", FileMode.Create, FileAccess.Write, FileShare.Read);
					using StreamWriter streamWriter3 = new StreamWriter(stream3);
					streamWriter3.WriteLine("{0} export log", saveFileDialog.FileName);
					streamWriter3.WriteLine("Created with Forza Studio 4.4 - Chipi's unofficial build" + Environment.NewLine);
					streamWriter3.WriteLine("mesh name\tvertex count\tface count\tmaterial name" + Environment.NewLine);
					foreach (ForzaMesh item4 in modelMeshes)
					{
						streamWriter3.WriteLine("{0}\t{1}\t{2}\t{3}", item4.Name, item4.VertexCount, item4.FaceCount, item4.MaterialName);
					}
				}
				MessageBox.Show("Extraction Complete!", "Finished", MessageBoxButtons.OK, MessageBoxIcon.Asterisk);
			}
		}
		UpdateStatus();
	}

	private int GetSelectedVertexCount(TreeNodeCollection nodes)
	{
		int num = 0;
		foreach (TreeNode node in nodes)
		{
			if (node.Checked && node.Tag != null && node.Tag.GetType() == typeof(ForzaMesh))
			{
				num += ((ForzaMesh)node.Tag).VertexCount;
			}
			num += GetSelectedVertexCount(node.Nodes);
		}
		return num;
	}

	private int GetSelectedFaceCount(TreeNodeCollection nodes)
	{
		int num = 0;
		foreach (TreeNode node in nodes)
		{
			if (node.Checked && node.Tag != null && node.Tag.GetType() == typeof(ForzaMesh))
			{
				num += ((ForzaMesh)node.Tag).FaceCount;
			}
			num += GetSelectedFaceCount(node.Nodes);
		}
		return num;
	}

	private List<ForzaMesh> GetModelMeshes(TreeNodeCollection nodes, bool selective)
	{
		List<ForzaMesh> list = new List<ForzaMesh>();
		foreach (TreeNode node in nodes)
		{
			if ((!selective || node.Checked) && node.Tag != null && node.Tag.GetType() == typeof(ForzaMesh))
			{
				list.Add(node.Tag as ForzaMesh);
			}
			list.AddRange(GetModelMeshes(node.Nodes, selective));
		}
		return list;
	}

	private void BindCameraSpeeds()
	{
		cmbViewportSpeed.Items.Clear();
		for (int i = 1; i <= 20; i++)
		{
			cmbViewportSpeed.Items.Add(new ComboBoxItem<float>(i, $"{i}x Camera Speed"));
		}
		cmbViewportSpeed.SelectedIndex = 0;
	}

	private void UpdateSelectedMeshStatus()
	{
		if (SelectedFaceCount > 0 && SelectedVertexCount > 0)
		{
			lblInformation.Text = $"Displaying {SelectedVertexCount} vertices and {SelectedFaceCount} faces";
		}
		else
		{
			lblInformation.Text = string.Empty;
		}
	}

	private void UpdateSelectedTextureStatus()
	{
		if (SelectedTexture != null)
		{
			lblInformation.Text = $"Selected texture dimensions of {SelectedTexture.Width}x{SelectedTexture.Height}";
		}
		else
		{
			lblInformation.Text = string.Empty;
		}
	}

	private void UpdateStatus(string text = null)
	{
		if (text == null)
		{
			if (tabForzaObjects.SelectedIndex == 0)
			{
				UpdateSelectedMeshStatus();
			}
			else
			{
				UpdateSelectedTextureStatus();
			}
		}
		else
		{
			lblInformation.Text = text;
		}
		Application.DoEvents();
	}

	private void BindUVset()
	{
		cmbExportUV.Items.Clear();
		cmbExportUV.Items.Add(new ComboBoxItem<float>(1f, "Export UV1"));
		cmbExportUV.Items.Add(new ComboBoxItem<float>(2f, "Export UV2"));
		cmbExportUV.SelectedIndex = 0;
	}

	private void mnuCreateLog_Click(object sender, EventArgs e)
	{
		CreateLog = true;
	}

	protected override void Dispose(bool disposing)
	{
		if (disposing && components != null)
		{
			components.Dispose();
		}
		base.Dispose(disposing);
	}

	private void InitializeComponent()
	{
		this.components = new System.ComponentModel.Container();
		System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(ForzaStudio.ForzaStudioForm));
		this.statusStrip1 = new System.Windows.Forms.StatusStrip();
		this.lblStatus = new System.Windows.Forms.ToolStripStatusLabel();
		this.lblInformation = new System.Windows.Forms.ToolStripStatusLabel();
		this.mnuMain = new System.Windows.Forms.MenuStrip();
		this.mnuFile = new System.Windows.Forms.ToolStripMenuItem();
		this.mnuImport = new System.Windows.Forms.ToolStripMenuItem();
		this.mnuExit = new System.Windows.Forms.ToolStripMenuItem();
		this.mnuUtilities = new System.Windows.Forms.ToolStripMenuItem();
		this.mnuUnpackArchive = new System.Windows.Forms.ToolStripMenuItem();
		this.mnuAbout = new System.Windows.Forms.ToolStripMenuItem();
		this.splitContainer1 = new System.Windows.Forms.SplitContainer();
		this.tabForzaObjects = new System.Windows.Forms.TabControl();
		this.tabModels = new System.Windows.Forms.TabPage();
		this.tvModels = new System.Windows.Forms.TreeView();
		this.ctxModelTreeMenu = new System.Windows.Forms.ContextMenuStrip(this.components);
		this.mnuExtractCheckedModels = new System.Windows.Forms.ToolStripMenuItem();
		this.mnuExtractAllModels = new System.Windows.Forms.ToolStripMenuItem();
		this.tabTextures = new System.Windows.Forms.TabPage();
		this.tvTextures = new System.Windows.Forms.TreeView();
		this.ctxTextureTreeMenu = new System.Windows.Forms.ContextMenuStrip(this.components);
		this.mnuExtractSelectedTextures = new System.Windows.Forms.ToolStripMenuItem();
		this.mnuExtractAllTextures = new System.Windows.Forms.ToolStripMenuItem();
		this.pnlTextureDisplay = new System.Windows.Forms.Panel();
		this.ctxTextureMenu = new System.Windows.Forms.ContextMenuStrip(this.components);
		this.mnuShowTextureAlpha = new System.Windows.Forms.ToolStripMenuItem();
		this.mnuSaveTextureAs = new System.Windows.Forms.ToolStripMenuItem();
		this.pnlViewport = new System.Windows.Forms.Panel();
		this.ctxViewportMenu = new System.Windows.Forms.ContextMenuStrip(this.components);
		this.mnuExportObj = new System.Windows.Forms.ToolStripMenuItem();
		this.mnuCreateLog = new System.Windows.Forms.ToolStripMenuItem();
		this.cmbExportUV = new System.Windows.Forms.ToolStripComboBox();
		this.toolStripSeparator1 = new System.Windows.Forms.ToolStripSeparator();
		this.mnuShowWireframe = new System.Windows.Forms.ToolStripMenuItem();
		this.cmbViewportSpeed = new System.Windows.Forms.ToolStripComboBox();
		this.statusStrip1.SuspendLayout();
		this.mnuMain.SuspendLayout();
		this.splitContainer1.Panel1.SuspendLayout();
		this.splitContainer1.Panel2.SuspendLayout();
		this.splitContainer1.SuspendLayout();
		this.tabForzaObjects.SuspendLayout();
		this.tabModels.SuspendLayout();
		this.ctxModelTreeMenu.SuspendLayout();
		this.tabTextures.SuspendLayout();
		this.ctxTextureTreeMenu.SuspendLayout();
		this.ctxTextureMenu.SuspendLayout();
		this.ctxViewportMenu.SuspendLayout();
		base.SuspendLayout();
		this.statusStrip1.Items.AddRange(new System.Windows.Forms.ToolStripItem[2] { this.lblStatus, this.lblInformation });
		this.statusStrip1.LayoutStyle = System.Windows.Forms.ToolStripLayoutStyle.HorizontalStackWithOverflow;
		this.statusStrip1.Location = new System.Drawing.Point(0, 660);
		this.statusStrip1.Name = "statusStrip1";
		this.statusStrip1.Size = new System.Drawing.Size(1264, 22);
		this.statusStrip1.TabIndex = 0;
		this.statusStrip1.Text = "statusStrip1";
		this.lblStatus.Name = "lblStatus";
		this.lblStatus.Size = new System.Drawing.Size(0, 17);
		this.lblInformation.Name = "lblInformation";
		this.lblInformation.Size = new System.Drawing.Size(0, 17);
		this.mnuMain.Items.AddRange(new System.Windows.Forms.ToolStripItem[3] { this.mnuFile, this.mnuUtilities, this.mnuAbout });
		this.mnuMain.Location = new System.Drawing.Point(0, 0);
		this.mnuMain.Name = "mnuMain";
		this.mnuMain.Size = new System.Drawing.Size(1264, 24);
		this.mnuMain.TabIndex = 1;
		this.mnuFile.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[2] { this.mnuImport, this.mnuExit });
		this.mnuFile.ForeColor = System.Drawing.SystemColors.ControlText;
		this.mnuFile.Name = "mnuFile";
		this.mnuFile.Size = new System.Drawing.Size(37, 20);
		this.mnuFile.Text = "File";
		this.mnuImport.Name = "mnuImport";
		this.mnuImport.Size = new System.Drawing.Size(110, 22);
		this.mnuImport.Text = "Import";
		this.mnuImport.Click += new System.EventHandler(mnuImport_Click);
		this.mnuExit.Name = "mnuExit";
		this.mnuExit.Size = new System.Drawing.Size(110, 22);
		this.mnuExit.Text = "Exit";
		this.mnuExit.Click += new System.EventHandler(mnuExit_Click);
		this.mnuUtilities.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[1] { this.mnuUnpackArchive });
		this.mnuUtilities.Name = "mnuUtilities";
		this.mnuUtilities.Size = new System.Drawing.Size(58, 20);
		this.mnuUtilities.Text = "Utilities";
		this.mnuUnpackArchive.Name = "mnuUnpackArchive";
		this.mnuUnpackArchive.Size = new System.Drawing.Size(157, 22);
		this.mnuUnpackArchive.Text = "Unpack Archive";
		this.mnuUnpackArchive.Click += new System.EventHandler(mnuExtractZip_Click);
		this.mnuAbout.Name = "mnuAbout";
		this.mnuAbout.Size = new System.Drawing.Size(52, 20);
		this.mnuAbout.Text = "About";
		this.mnuAbout.Click += new System.EventHandler(mnuAbout_Click);
		this.splitContainer1.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
		this.splitContainer1.Dock = System.Windows.Forms.DockStyle.Fill;
		this.splitContainer1.FixedPanel = System.Windows.Forms.FixedPanel.Panel1;
		this.splitContainer1.Location = new System.Drawing.Point(0, 24);
		this.splitContainer1.Name = "splitContainer1";
		this.splitContainer1.Panel1.Controls.Add(this.tabForzaObjects);
		this.splitContainer1.Panel1MinSize = 200;
		this.splitContainer1.Panel2.BackColor = System.Drawing.SystemColors.Control;
		this.splitContainer1.Panel2.Controls.Add(this.pnlTextureDisplay);
		this.splitContainer1.Panel2.Controls.Add(this.pnlViewport);
		this.splitContainer1.Size = new System.Drawing.Size(1264, 636);
		this.splitContainer1.SplitterDistance = 200;
		this.splitContainer1.SplitterWidth = 3;
		this.splitContainer1.TabIndex = 2;
		this.tabForzaObjects.Controls.Add(this.tabModels);
		this.tabForzaObjects.Controls.Add(this.tabTextures);
		this.tabForzaObjects.Dock = System.Windows.Forms.DockStyle.Fill;
		this.tabForzaObjects.Location = new System.Drawing.Point(0, 0);
		this.tabForzaObjects.Name = "tabForzaObjects";
		this.tabForzaObjects.SelectedIndex = 0;
		this.tabForzaObjects.Size = new System.Drawing.Size(198, 634);
		this.tabForzaObjects.TabIndex = 1;
		this.tabForzaObjects.Selecting += new System.Windows.Forms.TabControlCancelEventHandler(tabForzaObjects_Selecting);
		this.tabModels.Controls.Add(this.tvModels);
		this.tabModels.Location = new System.Drawing.Point(4, 22);
		this.tabModels.Name = "tabModels";
		this.tabModels.Padding = new System.Windows.Forms.Padding(3);
		this.tabModels.Size = new System.Drawing.Size(190, 608);
		this.tabModels.TabIndex = 0;
		this.tabModels.Text = "Models";
		this.tabModels.UseVisualStyleBackColor = true;
		this.tvModels.CheckBoxes = true;
		this.tvModels.ContextMenuStrip = this.ctxModelTreeMenu;
		this.tvModels.Dock = System.Windows.Forms.DockStyle.Fill;
		this.tvModels.Location = new System.Drawing.Point(3, 3);
		this.tvModels.Name = "tvModels";
		this.tvModels.Size = new System.Drawing.Size(184, 602);
		this.tvModels.TabIndex = 0;
		this.tvModels.AfterCheck += new System.Windows.Forms.TreeViewEventHandler(tvModels_AfterCheck);
		this.ctxModelTreeMenu.Items.AddRange(new System.Windows.Forms.ToolStripItem[2] { this.mnuExtractCheckedModels, this.mnuExtractAllModels });
		this.ctxModelTreeMenu.Name = "ctxModelMenu";
		this.ctxModelTreeMenu.Size = new System.Drawing.Size(159, 48);
		this.ctxModelTreeMenu.Opening += new System.ComponentModel.CancelEventHandler(ctxModelMenu_Opening);
		this.mnuExtractCheckedModels.Name = "mnuExtractCheckedModels";
		this.mnuExtractCheckedModels.Size = new System.Drawing.Size(158, 22);
		this.mnuExtractCheckedModels.Text = "Extract Checked";
		this.mnuExtractCheckedModels.Click += new System.EventHandler(mnuExtractCheckedModels_Click);
		this.mnuExtractAllModels.Name = "mnuExtractAllModels";
		this.mnuExtractAllModels.Size = new System.Drawing.Size(158, 22);
		this.mnuExtractAllModels.Text = "Extract All";
		this.mnuExtractAllModels.Click += new System.EventHandler(mnuExtractAllModels_Click);
		this.tabTextures.Controls.Add(this.tvTextures);
		this.tabTextures.Location = new System.Drawing.Point(4, 22);
		this.tabTextures.Name = "tabTextures";
		this.tabTextures.Padding = new System.Windows.Forms.Padding(3);
		this.tabTextures.Size = new System.Drawing.Size(190, 608);
		this.tabTextures.TabIndex = 1;
		this.tabTextures.Text = "Textures";
		this.tabTextures.UseVisualStyleBackColor = true;
		this.tvTextures.CheckBoxes = true;
		this.tvTextures.ContextMenuStrip = this.ctxTextureTreeMenu;
		this.tvTextures.Dock = System.Windows.Forms.DockStyle.Fill;
		this.tvTextures.Location = new System.Drawing.Point(3, 3);
		this.tvTextures.Name = "tvTextures";
		this.tvTextures.Size = new System.Drawing.Size(184, 602);
		this.tvTextures.TabIndex = 0;
		this.tvTextures.AfterSelect += new System.Windows.Forms.TreeViewEventHandler(tvTextures_AfterSelect);
		this.ctxTextureTreeMenu.Items.AddRange(new System.Windows.Forms.ToolStripItem[2] { this.mnuExtractSelectedTextures, this.mnuExtractAllTextures });
		this.ctxTextureTreeMenu.Name = "ctxTextureMenu";
		this.ctxTextureTreeMenu.Size = new System.Drawing.Size(159, 48);
		this.ctxTextureTreeMenu.Opening += new System.ComponentModel.CancelEventHandler(ctxTextureTreeMenu_Opening);
		this.mnuExtractSelectedTextures.Name = "mnuExtractSelectedTextures";
		this.mnuExtractSelectedTextures.Size = new System.Drawing.Size(158, 22);
		this.mnuExtractSelectedTextures.Text = "Extract Checked";
		this.mnuExtractSelectedTextures.Click += new System.EventHandler(mnuExtractCheckedTextures_Click);
		this.mnuExtractAllTextures.Name = "mnuExtractAllTextures";
		this.mnuExtractAllTextures.Size = new System.Drawing.Size(158, 22);
		this.mnuExtractAllTextures.Text = "Extract All";
		this.mnuExtractAllTextures.Click += new System.EventHandler(mnuExtractAllTextures_Click);
		this.pnlTextureDisplay.BackColor = System.Drawing.Color.FromArgb(153, 180, 209);
		this.pnlTextureDisplay.ContextMenuStrip = this.ctxTextureMenu;
		this.pnlTextureDisplay.Dock = System.Windows.Forms.DockStyle.Fill;
		this.pnlTextureDisplay.Location = new System.Drawing.Point(0, 0);
		this.pnlTextureDisplay.Name = "pnlTextureDisplay";
		this.pnlTextureDisplay.Size = new System.Drawing.Size(1059, 634);
		this.pnlTextureDisplay.TabIndex = 1;
		this.pnlTextureDisplay.Visible = false;
		this.pnlTextureDisplay.Paint += new System.Windows.Forms.PaintEventHandler(pnlTextureDisplay_Paint);
		this.pnlTextureDisplay.Resize += new System.EventHandler(pnlTextureDisplay_Resize);
		this.ctxTextureMenu.Items.AddRange(new System.Windows.Forms.ToolStripItem[2] { this.mnuShowTextureAlpha, this.mnuSaveTextureAs });
		this.ctxTextureMenu.Name = "ctxTextureMenuDetails";
		this.ctxTextureMenu.Size = new System.Drawing.Size(185, 48);
		this.ctxTextureMenu.Opening += new System.ComponentModel.CancelEventHandler(ctxTextureMenu_Opening);
		this.mnuShowTextureAlpha.CheckOnClick = true;
		this.mnuShowTextureAlpha.Name = "mnuShowTextureAlpha";
		this.mnuShowTextureAlpha.Size = new System.Drawing.Size(184, 22);
		this.mnuShowTextureAlpha.Text = "Show Alpha Channel";
		this.mnuShowTextureAlpha.CheckedChanged += new System.EventHandler(mnuShowTextureAlpha_CheckedChanged);
		this.mnuSaveTextureAs.Name = "mnuSaveTextureAs";
		this.mnuSaveTextureAs.Size = new System.Drawing.Size(184, 22);
		this.mnuSaveTextureAs.Text = "Save As...";
		this.mnuSaveTextureAs.Click += new System.EventHandler(mnuSaveTextureAs_Click);
		this.pnlViewport.BackColor = System.Drawing.Color.FromArgb(153, 180, 209);
		this.pnlViewport.ContextMenuStrip = this.ctxViewportMenu;
		this.pnlViewport.Dock = System.Windows.Forms.DockStyle.Fill;
		this.pnlViewport.Location = new System.Drawing.Point(0, 0);
		this.pnlViewport.Name = "pnlViewport";
		this.pnlViewport.Size = new System.Drawing.Size(1059, 634);
		this.pnlViewport.TabIndex = 0;
		this.pnlViewport.Paint += new System.Windows.Forms.PaintEventHandler(pnlViewport_Paint);
		this.pnlViewport.Resize += new System.EventHandler(pnlViewport_Resize);
		this.ctxViewportMenu.Items.AddRange(new System.Windows.Forms.ToolStripItem[6] { this.mnuExportObj, this.mnuCreateLog, this.cmbExportUV, this.toolStripSeparator1, this.mnuShowWireframe, this.cmbViewportSpeed });
		this.ctxViewportMenu.Name = "ctxViewportMenu";
		this.ctxViewportMenu.Size = new System.Drawing.Size(192, 130);
		this.ctxViewportMenu.Opening += new System.ComponentModel.CancelEventHandler(ctxViewportMenu_Opening);
		this.mnuExportObj.Name = "mnuExportObj";
		this.mnuExportObj.Size = new System.Drawing.Size(191, 22);
		this.mnuExportObj.Text = "Export Wavefront .OBJ";
		this.mnuExportObj.Click += new System.EventHandler(mnuExportObj_Click);
		this.mnuCreateLog.CheckOnClick = true;
		this.mnuCreateLog.Name = "mnuCreateLog";
		this.mnuCreateLog.Size = new System.Drawing.Size(191, 22);
		this.mnuCreateLog.Text = "Create Export Log";
		this.mnuCreateLog.Click += new System.EventHandler(mnuCreateLog_Click);
		this.cmbExportUV.Items.AddRange(new object[2] { "Export UV1", "Export UV2" });
		this.cmbExportUV.Name = "cmbExportUV";
		this.cmbExportUV.Size = new System.Drawing.Size(121, 23);
		this.toolStripSeparator1.Name = "toolStripSeparator1";
		this.toolStripSeparator1.Size = new System.Drawing.Size(188, 6);
		this.mnuShowWireframe.CheckOnClick = true;
		this.mnuShowWireframe.Name = "mnuShowWireframe";
		this.mnuShowWireframe.Size = new System.Drawing.Size(191, 22);
		this.mnuShowWireframe.Text = "Show Wireframe";
		this.mnuShowWireframe.Click += new System.EventHandler(mnuShowWireframe_Click);
		this.cmbViewportSpeed.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
		this.cmbViewportSpeed.Items.AddRange(new object[2] { "1x Camera Speed", "2x Camera Speed" });
		this.cmbViewportSpeed.Name = "cmbViewportSpeed";
		this.cmbViewportSpeed.Size = new System.Drawing.Size(121, 23);
		base.AutoScaleDimensions = new System.Drawing.SizeF(6f, 13f);
		base.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
		base.ClientSize = new System.Drawing.Size(1264, 682);
		base.Controls.Add(this.splitContainer1);
		base.Controls.Add(this.statusStrip1);
		base.Controls.Add(this.mnuMain);
		this.DoubleBuffered = true;
		base.Icon = (System.Drawing.Icon)resources.GetObject("$this.Icon");
		base.MainMenuStrip = this.mnuMain;
		this.MinimumSize = new System.Drawing.Size(640, 480);
		base.Name = "ForzaStudioForm";
		this.Text = "Forza Studio 4.4 - Chipi's unofficial build - Forza Motorsport Resource Extraction Tool";
		base.Shown += new System.EventHandler(ForzaStudioForm_Shown);
		base.MouseWheel += new System.Windows.Forms.MouseEventHandler(Form1_MouseWheel);
		this.statusStrip1.ResumeLayout(false);
		this.statusStrip1.PerformLayout();
		this.mnuMain.ResumeLayout(false);
		this.mnuMain.PerformLayout();
		this.splitContainer1.Panel1.ResumeLayout(false);
		this.splitContainer1.Panel2.ResumeLayout(false);
		this.splitContainer1.ResumeLayout(false);
		this.tabForzaObjects.ResumeLayout(false);
		this.tabModels.ResumeLayout(false);
		this.ctxModelTreeMenu.ResumeLayout(false);
		this.tabTextures.ResumeLayout(false);
		this.ctxTextureTreeMenu.ResumeLayout(false);
		this.ctxTextureMenu.ResumeLayout(false);
		this.ctxViewportMenu.ResumeLayout(false);
		base.ResumeLayout(false);
		base.PerformLayout();
	}
}
