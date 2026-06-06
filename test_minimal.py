# test_minimal.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

app = FastAPI()

# Create templates directory if it doesn't exist
templates_dir = Path("test_templates")
templates_dir.mkdir(exist_ok=True)

# Create a simple template
template_content = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<h1>Hello {{ name }}!</h1>
<p>Request: {{ request.url.path }}</p>
</body>
</html>"""

with open(templates_dir / "test.html", "w") as f:
    f.write(template_content)

# Initialize templates
templates = Jinja2Templates(directory=str(templates_dir))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "test.html",  # Use the template name as a string
        {"request": request, "name": "World"}
    )

if __name__ == "__main__":
    import uvicorn
    print(f"Templates directory: {templates_dir.absolute()}")
    print(f"Template exists: {(templates_dir / 'test.html').exists()}")
    uvicorn.run(app, host="127.0.0.1", port=8000)