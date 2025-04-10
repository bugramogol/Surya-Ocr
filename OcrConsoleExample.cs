using System;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using SuryaOcrClient;
using Newtonsoft.Json;

namespace SuryaOcrConsoleExample
{
    class Program
    {
        static async Task Main(string[] args)
        {
            Console.WriteLine("Surya OCR Console Example");
            Console.WriteLine("========================");
            
            // Surya OCR API base URL
            string apiUrl = "http://localhost:5000";
            var ocrClient = new SuryaOcrClient.SuryaOcrClient(apiUrl);
            
            try
            {
                // Örnek 1: Dosyadan OCR işlemi
                if (args.Length > 0 && File.Exists(args[0]))
                {
                    Console.WriteLine($"Dosyadan OCR işlemi yapılıyor: {args[0]}");
                    var result = await ocrClient.PerformOcrAsync(args[0]);
                    Console.WriteLine("\nOCR Sonucu (Dosya):");
                    Console.WriteLine(result.Text);
                }
                
                // Örnek 2: URL'den resmi indirip byte[] olarak OCR işlemi
                string imageUrl = "https://raw.githubusercontent.com/tesseract-ocr/tessdata/main/eng.training_text.png";
                Console.WriteLine($"\nURL'den resim indirilerek OCR işlemi yapılıyor: {imageUrl}");
                
                using (var httpClient = new HttpClient())
                {
                    // Resmi indir
                    var imageBytes = await httpClient.GetByteArrayAsync(imageUrl);
                    Console.WriteLine($"İndirilen resim boyutu: {imageBytes.Length} byte");
                    
                    // OCR işlemi yap
                    var result = await ocrClient.PerformOcrAsync(imageBytes, "sample.png", "en");
                    Console.WriteLine("\nOCR Sonucu (byte[]):");
                    Console.WriteLine(result.Text);
                    
                    // Örnek 3: byte[] verisini MemoryStream'e dönüştürerek OCR işlemi
                    Console.WriteLine("\nAynı veri MemoryStream kullanılarak OCR işlemi yapılıyor");
                    
                    using (var ms = new MemoryStream(imageBytes))
                    {
                        var msResult = await ocrClient.PerformOcrAsync(ms, "sample.png", "en");
                        Console.WriteLine("\nOCR Sonucu (MemoryStream):");
                        Console.WriteLine(msResult.Text);
                    }
                }
                
                // Örnek 4: Bellek üzerinde oluşturulan bir resmi OCR işlemine sokma (gerçek uygulamada farklı olabilir)
                Console.WriteLine("\nBellek üzerinde oluşturulan resim verisi kullanılarak OCR işlemi yapılıyor");
                
                // Dinamik oluşturulan bir veri - gerçek bir uygulama senaryosunda bu 
                // örneğin bir kamera akışından, ekran görüntüsünden veya başka bir kaynaktan gelebilir
                byte[] sampleImageData = File.Exists("sample.jpg") ? File.ReadAllBytes("sample.jpg") : null;
                
                if (sampleImageData != null)
                {
                    var result = await ocrClient.PerformOcrAsync(sampleImageData, "dynamic_image.jpg", "en");
                    Console.WriteLine("\nOCR Sonucu (Dinamik veri):");
                    Console.WriteLine(result.Text);
                }
                else
                {
                    Console.WriteLine("Örnek resim dosyası bulunamadı, dinamik veri örneği atlanıyor.");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Hata: {ex.Message}");
            }
            
            Console.WriteLine("\nİşlem tamamlandı. Çıkmak için bir tuşa basın.");
            Console.ReadKey();
        }
    }
} 