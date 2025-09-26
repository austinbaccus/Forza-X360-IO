using System;
using System.Windows.Forms;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;

namespace ForzaStudio;

public class RenderScene : IDisposable
{
	private GraphicsDevice Graphics;

	private BasicEffect Ambiance;

	private BasicEffect ColoredVertices;

	private bool GraphicsDisabled;

	public TreeView Models { get; private set; }

	public Panel Viewport { get; private set; }

	public Camera Camera { get; private set; }

	public bool ShowWireframe { get; set; }

	public RenderScene(ref TreeView models, ref Panel viewport)
	{
		if (models == null || viewport == null)
		{
			throw new ArgumentNullException();
		}
		Viewport = viewport;
		Models = models;
		Camera = new Camera(viewport);
		try
		{
			InitializeGraphicsDevice();
			Update(forceRedraw: true);
		}
		catch (Exception)
		{
			GraphicsDisabled = true;
			MessageBox.Show("Graphics card incompatibility detected. The model viewport will remain disabled.");
		}
	}

	~RenderScene()
	{
		Dispose();
	}

	public void Update(bool forceRedraw = false)
	{
		try
		{
			if (GraphicsDisabled)
			{
				return;
			}
			Camera.Update(Viewport.Width, Viewport.Height);
			if (forceRedraw || Camera.HasChanged)
			{
				Ambiance.View = Camera.View;
				Ambiance.Projection = Camera.Projection;
				Ambiance.World = Camera.World;
				Ambiance.DirectionalLight0.Direction = Camera.ForwardDirection;
				ColoredVertices.View = Camera.View;
				ColoredVertices.Projection = Camera.Projection;
				ColoredVertices.World = Camera.World;
				Graphics.Clear(new Color(153, 180, 209, byte.MaxValue));
				DrawGrid(10, 1f);
				DrawCheckedModels(Models.Nodes, FillMode.Solid);
				if (ShowWireframe)
				{
					DrawCheckedModels(Models.Nodes, FillMode.WireFrame);
				}
				Graphics.Present();
			}
		}
		catch (Exception)
		{
		}
	}

	private void InitializeGraphicsDevice()
	{
		if (!GraphicsDisabled)
		{
			PresentationParameters presentationParameters = new PresentationParameters();
			presentationParameters.IsFullScreen = false;
			presentationParameters.BackBufferCount = 2;
			presentationParameters.BackBufferWidth = Viewport.Width;
			presentationParameters.BackBufferHeight = Viewport.Height;
			presentationParameters.BackBufferFormat = SurfaceFormat.Unknown;
			presentationParameters.EnableAutoDepthStencil = true;
			presentationParameters.AutoDepthStencilFormat = DepthFormat.Depth24Stencil8;
			presentationParameters.PresentationInterval = PresentInterval.Default;
			Graphics = new GraphicsDevice(GraphicsAdapter.DefaultAdapter, DeviceType.Hardware, Viewport.Handle, presentationParameters);
			Graphics.RenderState.CullMode = CullMode.CullClockwiseFace;
			Ambiance = new BasicEffect(Graphics, null);
			Ambiance.Alpha = 1f;
			Ambiance.DiffuseColor = new Vector3(0.75f, 0.75f, 0.75f);
			Ambiance.SpecularColor = new Vector3(0.75f, 0.75f, 0.75f);
			Ambiance.SpecularPower = 25f;
			Ambiance.AmbientLightColor = new Vector3(0.75f, 0.75f, 0.75f);
			Ambiance.LightingEnabled = true;
			Ambiance.EnableDefaultLighting();
			Ambiance.VertexColorEnabled = true;
			Ambiance.DirectionalLight0.Enabled = true;
			Ambiance.DirectionalLight0.DiffuseColor = Vector3.One;
			Ambiance.DirectionalLight0.SpecularColor = new Vector3(0.75f, 0.75f, 0.75f);
			Ambiance.DirectionalLight1.Enabled = true;
			Ambiance.DirectionalLight1.DiffuseColor = Vector3.One;
			Ambiance.DirectionalLight1.SpecularColor = new Vector3(0.75f, 0.75f, 0.75f);
			Ambiance.DirectionalLight1.Direction = new Vector3(0f, -1f, 0f);
			ColoredVertices = new BasicEffect(Graphics, null);
			ColoredVertices.Alpha = 1f;
			ColoredVertices.DiffuseColor = Vector3.One;
			ColoredVertices.AmbientLightColor = Vector3.One;
			ColoredVertices.VertexColorEnabled = true;
		}
	}

	public void Dispose()
	{
		if (Graphics != null)
		{
			Graphics.Dispose();
		}
		if (Ambiance != null)
		{
			Ambiance.Dispose();
		}
		if (ColoredVertices != null)
		{
			ColoredVertices.Dispose();
		}
	}

	public void ResetGraphicsDevice()
	{
		Dispose();
		InitializeGraphicsDevice();
		Update(forceRedraw: true);
	}

	private void DrawCheckedModels(TreeNodeCollection nodes, FillMode fill)
	{
		switch (fill)
		{
		case FillMode.Solid:
			Ambiance.VertexColorEnabled = true;
			Ambiance.DiffuseColor = new Vector3(0.7f, 0.7f, 0.7f);
			Graphics.RenderState.FillMode = FillMode.Solid;
			break;
		case FillMode.WireFrame:
			Ambiance.VertexColorEnabled = false;
			Graphics.RenderState.FillMode = FillMode.WireFrame;
			Ambiance.DiffuseColor = new Vector3(0f, 0f, 0f);
			break;
		}
		foreach (TreeNode node in nodes)
		{
			DrawCheckedModels(node.Nodes, fill);
			if (!node.Checked || node.Tag == null || node.Tag.GetType() != typeof(ForzaMesh))
			{
				continue;
			}
			Ambiance.Begin();
			foreach (EffectPass pass in Ambiance.CurrentTechnique.Passes)
			{
				pass.Begin();
				ForzaMesh forzaMesh = node.Tag as ForzaMesh;
				forzaMesh.Draw(ref Graphics);
				pass.End();
			}
			Ambiance.End();
		}
	}

	private void DrawGrid(int size, float spacing)
	{
		ColoredVertices.Begin();
		foreach (EffectPass pass in ColoredVertices.CurrentTechnique.Passes)
		{
			pass.Begin();
			float num = (float)size * spacing / 2f;
			int num2 = (size + 1) * 4;
			VertexPositionColor[] array = new VertexPositionColor[num2 + 2];
			for (int i = 0; i < num2; i += 4)
			{
				float num3 = 0f - num + (float)(i / 4) * spacing;
				ref VertexPositionColor reference = ref array[i];
				reference = new VertexPositionColor(new Vector3(0f - num, 0f, num3), Color.DarkGreen);
				ref VertexPositionColor reference2 = ref array[i + 1];
				reference2 = new VertexPositionColor(new Vector3(num, 0f, num3), Color.White);
				ref VertexPositionColor reference3 = ref array[i + 2];
				reference3 = new VertexPositionColor(new Vector3(num3, 0f, 0f - num), Color.DarkBlue);
				ref VertexPositionColor reference4 = ref array[i + 3];
				reference4 = new VertexPositionColor(new Vector3(num3, 0f, num), Color.White);
			}
			ref VertexPositionColor reference5 = ref array[num2];
			reference5 = new VertexPositionColor(new Vector3(0f, 0f - num, 0f), Color.DarkRed);
			ref VertexPositionColor reference6 = ref array[num2 + 1];
			reference6 = new VertexPositionColor(new Vector3(0f, num, 0f), Color.White);
			Graphics.VertexDeclaration = new VertexDeclaration(Graphics, VertexPositionColor.VertexElements);
			Graphics.DrawUserPrimitives(PrimitiveType.LineList, array, 0, array.Length / 2);
			pass.End();
		}
		ColoredVertices.End();
	}
}
