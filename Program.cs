using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.AspNetCore.Http;
using System;
using System.IO;
using SuryaOcrClient;
using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json;

var builder = WebApplication.CreateBuilder(args);

// Add services
builder.Services.AddSingleton<SuryaOcrClient.SuryaOcrClient>(provider => 
    new SuryaOcrClient.SuryaOcrClient("http://localhost:5000"));

// Add for file uploads
builder.Services.AddControllersWithViews();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}

app.UseStaticFiles();
app.UseRouting();

app.MapGet("/", async context =>
{
    await context.Response.WriteAsync("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Surya OCR Client</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .result { margin-top: 20px; padding: 10px; border: 1px solid #ddd; min-height: 100px; }
            .loading { display: none; margin-top: 10px; }
            img { max-width: 100%; }
            .tabs { display: flex; margin-bottom: 20px; }
            .tab { padding: 10px 20px; cursor: pointer; background: #f0f0f0; border: 1px solid #ddd; }
            .tab.active { background: #fff; border-bottom: 1px solid #fff; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Surya OCR Example</h1>
            
            <div class="tabs">
                <div class="tab active" data-tab="upload">Upload File</div>
                <div class="tab" data-tab="url">Image URL</div>
            </div>
            
            <div class="tab-content active" id="upload-tab">
                <form id="ocrForm" enctype="multipart/form-data" method="post" action="/ocr">
                    <div>
                        <label for="imageFile">Select Image:</label>
                        <input type="file" id="imageFile" name="imageFile" accept="image/*" required />
                    </div>
                    <div>
                        <label for="languages">Languages (comma-separated):</label>
                        <input type="text" id="languages" name="languages" value="en" />
                    </div>
                    <div>
                        <button type="submit">Extract Text</button>
                    </div>
                    <div class="loading" id="loading-upload">Processing... Please wait.</div>
                </form>
            </div>
            
            <div class="tab-content" id="url-tab">
                <form id="urlForm">
                    <div>
                        <label for="imageUrl">Image URL:</label>
                        <input type="url" id="imageUrl" name="imageUrl" required />
                    </div>
                    <div>
                        <label for="urlLanguages">Languages (comma-separated):</label>
                        <input type="text" id="urlLanguages" name="urlLanguages" value="en" />
                    </div>
                    <div>
                        <button type="submit">Extract Text</button>
                    </div>
                    <div class="loading" id="loading-url">Processing... Please wait.</div>
                </form>
            </div>
            
            <div class="result" id="result">
                <div id="preview"></div>
                <pre id="extractedText"></pre>
            </div>
        </div>
        <script>
            // Tab handling
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    // Remove active class from all tabs and tab contents
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    
                    // Add active class to clicked tab
                    tab.classList.add('active');
                    
                    // Show corresponding tab content
                    const tabName = tab.getAttribute('data-tab');
                    document.getElementById(`${tabName}-tab`).classList.add('active');
                });
            });
            
            // File upload form
            document.getElementById('ocrForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const loading = document.getElementById('loading-upload');
                const result = document.getElementById('result');
                const preview = document.getElementById('preview');
                const extractedText = document.getElementById('extractedText');
                
                loading.style.display = 'block';
                extractedText.textContent = '';
                
                const formData = new FormData(this);
                
                try {
                    const response = await fetch('/ocr', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        throw new Error('OCR request failed');
                    }
                    
                    const data = await response.json();
                    
                    // Display image preview
                    const file = document.getElementById('imageFile').files[0];
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        preview.innerHTML = `<img src="${e.target.result}" alt="Uploaded image" />`;
                    };
                    reader.readAsDataURL(file);
                    
                    // Display OCR result
                    extractedText.textContent = data.text;
                } catch (error) {
                    extractedText.textContent = 'Error: ' + error.message;
                } finally {
                    loading.style.display = 'none';
                }
            });
            
            // URL form
            document.getElementById('urlForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const loading = document.getElementById('loading-url');
                const result = document.getElementById('result');
                const preview = document.getElementById('preview');
                const extractedText = document.getElementById('extractedText');
                
                loading.style.display = 'block';
                extractedText.textContent = '';
                
                const imageUrl = document.getElementById('imageUrl').value;
                const languages = document.getElementById('urlLanguages').value;
                
                try {
                    const response = await fetch('/ocr-url', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ imageUrl, languages })
                    });
                    
                    if (!response.ok) {
                        throw new Error('OCR request failed');
                    }
                    
                    const data = await response.json();
                    
                    // Display image preview
                    preview.innerHTML = `<img src="${imageUrl}" alt="Remote image" />`;
                    
                    // Display OCR result
                    extractedText.textContent = data.text;
                } catch (error) {
                    extractedText.textContent = 'Error: ' + error.message;
                } finally {
                    loading.style.display = 'none';
                }
            });
        </script>
    </body>
    </html>
    """);
});

// Handle file upload
app.MapPost("/ocr", async (HttpContext context, SuryaOcrClient.SuryaOcrClient ocrClient) =>
{
    try
    {
        var form = await context.Request.ReadFormAsync();
        var file = form.Files["imageFile"];
        var languages = form.ContainsKey("languages") ? form["languages"].ToString() : "en";
        
        if (file == null || file.Length == 0)
        {
            return Results.BadRequest("No file uploaded");
        }
        
        // Save the uploaded file temporarily
        var tempFilePath = Path.GetTempFileName();
        try
        {
            using (var stream = new FileStream(tempFilePath, FileMode.Create))
            {
                await file.CopyToAsync(stream);
            }
            
            // Use the OCR client to process the image
            var result = await ocrClient.PerformOcrAsync(tempFilePath, languages);
            
            return Results.Json(result);
        }
        finally
        {
            // Clean up the temporary file
            if (File.Exists(tempFilePath))
            {
                File.Delete(tempFilePath);
            }
        }
    }
    catch (Exception ex)
    {
        return Results.Problem("Error processing image: " + ex.Message);
    }
});

// Handle URL-based OCR (uses byte[] method)
app.MapPost("/ocr-url", async (HttpContext context, SuryaOcrClient.SuryaOcrClient ocrClient) =>
{
    try
    {
        // Get image URL and languages from request
        using var reader = new StreamReader(context.Request.Body);
        var requestBody = await reader.ReadToEndAsync();
        var requestData = JsonConvert.DeserializeObject<UrlRequestData>(requestBody);
        
        if (string.IsNullOrEmpty(requestData?.ImageUrl))
        {
            return Results.BadRequest("No image URL provided");
        }
        
        // Download the image using HttpClient
        using var httpClient = new HttpClient();
        byte[] imageBytes = await httpClient.GetByteArrayAsync(requestData.ImageUrl);
        
        // Extract filename from URL for MIME type detection
        var uri = new Uri(requestData.ImageUrl);
        var filename = Path.GetFileName(uri.LocalPath);
        
        // Use the OCR client's byte[] method to process the image
        var result = await ocrClient.PerformOcrAsync(imageBytes, filename, requestData.Languages ?? "en");
        
        return Results.Json(result);
    }
    catch (Exception ex)
    {
        return Results.Problem("Error processing image: " + ex.Message);
    }
});

// Alternative endpoint that uses MemoryStream (for demonstration purposes)
app.MapPost("/ocr-stream", async (HttpContext context, SuryaOcrClient.SuryaOcrClient ocrClient) =>
{
    try
    {
        var form = await context.Request.ReadFormAsync();
        var file = form.Files["imageFile"];
        var languages = form.ContainsKey("languages") ? form["languages"].ToString() : "en";
        
        if (file == null || file.Length == 0)
        {
            return Results.BadRequest("No file uploaded");
        }
        
        // Load the file directly into a MemoryStream
        using var memoryStream = new MemoryStream();
        await file.CopyToAsync(memoryStream);
        
        // Reset stream position to beginning
        memoryStream.Position = 0;
        
        // Use the OCR client's MemoryStream method to process the image
        var result = await ocrClient.PerformOcrAsync(memoryStream, file.FileName, languages);
        
        return Results.Json(result);
    }
    catch (Exception ex)
    {
        return Results.Problem("Error processing image: " + ex.Message);
    }
});

// Class to deserialize JSON request for URL-based OCR
class UrlRequestData
{
    public string ImageUrl { get; set; }
    public string Languages { get; set; }
}

app.Run(); 