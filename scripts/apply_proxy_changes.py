import os
import subprocess
import sys

# Define base paths
BASE_DIR = os.getcwd()
PARCELS_VIEWS = os.path.join(BASE_DIR, 'parcels', 'views.py')
PARCELS_URLS = os.path.join(BASE_DIR, 'parcels', 'urls.py')

def modify_views():
    try:
        with open(PARCELS_VIEWS, 'r', encoding='utf-8') as f:
            content = f.read()

        if "def geocode_proxy(" not in content:
            print("Adding geocode_proxy to views.py...")
            
            user_code = """

# --- GEOCODING PROXY ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def geocode_proxy(request):
    \"\"\"
    Proxy para geocodificación usando Nominatim.
    \"\"\"
    try:
        query = request.GET.get('q')
        if not query:
            return Response({"error": "Parámetro 'q' es requerido"}, status=400)

        headers = { 'User-Agent': 'AgroTechDigital/1.0 (internal-proxy)', 'Referer': 'https://agrotechcolombia.com' }
        url = "https://nominatim.openstreetmap.org/search"
        params = { 'q': query, 'format': 'json', 'limit': 5, 'addressdetails': 1, 'countrycodes': 'co', 'accept-language': 'es' }
        
        external_response = requests.get(url, params=params, headers=headers)
        if external_response.status_code != 200:
             logger.error(f"Error Nominatim: {external_response.status_code}")
             return Response({"error": "Error externo"}, status=502)
        
        return Response(external_response.json())
    except Exception as e:
        logger.error(f"Error geocode: {e}")
        return Response({"error": "Error interno"}, status=500)
"""
            with open(PARCELS_VIEWS, 'a', encoding='utf-8') as f:
                f.write(user_code)
        else:
            print("geocode_proxy already exists in views.py")
    except Exception as e:
        print(f"Error modifying views.py: {e}")

def modify_urls():
    try:
        with open(PARCELS_URLS, 'r', encoding='utf-8') as f:
            content = f.read()

        if "path('geocode/'," not in content:
            print("Adding geocode path to urls.py...")
            if "urlpatterns = [" in content:
                new_line = "\n    # Geocoding Proxy\n    path('geocode/', views.geocode_proxy, name='geocode_proxy'),"
                content = content.replace("urlpatterns = [", "urlpatterns = [" + new_line, 1)
                
                with open(PARCELS_URLS, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                print("Could not find 'urlpatterns = [' in urls.py")
        else:
            print("geocode path already exists in urls.py")
    except Exception as e:
        print(f"Error modifying urls.py: {e}")

def run_git_commands():
    commands = [
        ["git", "add", "parcels/views.py", "parcels/urls.py"],
        ["git", "commit", "--amend", "--no-edit"],
        ["git", "push", "origin", "main", "--force"]
    ]
    
    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            if result.returncode != 0:
                print(f"Command failed with code {result.returncode}")
        except Exception as e:
            print(f"Error executing command {' '.join(cmd)}: {e}")

if __name__ == "__main__":
    modify_views()
    modify_urls()
    run_git_commands()
