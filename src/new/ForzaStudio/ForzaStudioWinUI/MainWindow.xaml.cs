using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;
using System.Threading.Tasks;
using Windows.Storage.Pickers;

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
            // Create the file picker
            var filePicker = new FileOpenPicker();

            // Get the current window's HWND by passing in the Window object
            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);

            // Associate the HWND with the file picker
            WinRT.Interop.InitializeWithWindow.Initialize(filePicker, hwnd);

            // Use file picker like normal!
            filePicker.FileTypeFilter.Add(".zip");
            var file = await filePicker.PickSingleFileAsync();
        }

        private async void ExportFile(object sender, RoutedEventArgs e)
        {
            // Create the file picker
            var filePicker = new FileOpenPicker();

            // Get the current window's HWND by passing in the Window object
            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);

            // Associate the HWND with the file picker
            WinRT.Interop.InitializeWithWindow.Initialize(filePicker, hwnd);

            // Use file picker like normal!
            filePicker.FileTypeFilter.Add(".zip");
            var file = await filePicker.PickSingleFileAsync();
        }
    }
}
