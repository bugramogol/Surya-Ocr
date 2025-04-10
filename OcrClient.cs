using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.IO;
using System.Threading.Tasks;
using System.Text.Json.Serialization;
using System.Collections.Generic;

namespace SuryaOcrClient
{
    public class OcrResult
    {
        [JsonPropertyName("text")]
        public string Text { get; set; }
        
        [JsonPropertyName("details")]
        public List<TextDetail> Details { get; set; }
        
        public class TextDetail
        {
            [JsonPropertyName("text")]
            public string Text { get; set; }
            
            [JsonPropertyName("bbox")]
            public float[] BoundingBox { get; set; }
        }
    }
    
    public class SuryaOcrClient
    {
        private readonly HttpClient _httpClient;
        private readonly string _apiBaseUrl;
        
        public SuryaOcrClient(string apiBaseUrl)
        {
            _httpClient = new HttpClient();
            _apiBaseUrl = apiBaseUrl.TrimEnd('/');
        }
        
        public async Task<OcrResult> PerformOcrAsync(string imagePath, string languages = "en")
        {
            using var multipartContent = new MultipartFormDataContent();
            
            // Add the image file
            var fileBytes = await File.ReadAllBytesAsync(imagePath);
            var imageContent = new ByteArrayContent(fileBytes);
            multipartContent.Add(imageContent, "image", Path.GetFileName(imagePath));
            
            // Add language parameter
            multipartContent.Add(new StringContent(languages), "langs");
            
            // Send the request
            var response = await _httpClient.PostAsync($"{_apiBaseUrl}/ocr", multipartContent);
            
            // Handle the response
            response.EnsureSuccessStatusCode();
            var result = await response.Content.ReadFromJsonAsync<OcrResult>();
            
            return result;
        }
        
        /// <summary>
        /// Performs OCR on an image provided as a byte array
        /// </summary>
        /// <param name="imageBytes">The image data as a byte array</param>
        /// <param name="filename">Name of the file (used for content type detection)</param>
        /// <param name="languages">Comma-separated list of language codes</param>
        /// <returns>OCR result with extracted text</returns>
        public async Task<OcrResult> PerformOcrAsync(byte[] imageBytes, string filename, string languages = "en")
        {
            using var multipartContent = new MultipartFormDataContent();
            
            // Add the image from byte array
            var imageContent = new ByteArrayContent(imageBytes);
            multipartContent.Add(imageContent, "image", filename);
            
            // Add language parameter
            multipartContent.Add(new StringContent(languages), "langs");
            
            // Send the request
            var response = await _httpClient.PostAsync($"{_apiBaseUrl}/ocr", multipartContent);
            
            // Handle the response
            response.EnsureSuccessStatusCode();
            var result = await response.Content.ReadFromJsonAsync<OcrResult>();
            
            return result;
        }
        
        /// <summary>
        /// Performs OCR on an image provided as a MemoryStream
        /// </summary>
        /// <param name="imageStream">The image data as a MemoryStream</param>
        /// <param name="filename">Name of the file (used for content type detection)</param>
        /// <param name="languages">Comma-separated list of language codes</param>
        /// <returns>OCR result with extracted text</returns>
        public async Task<OcrResult> PerformOcrAsync(MemoryStream imageStream, string filename, string languages = "en")
        {
            // Convert MemoryStream to byte array
            byte[] imageBytes = imageStream.ToArray();
            return await PerformOcrAsync(imageBytes, filename, languages);
        }
    }
} 