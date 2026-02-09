"""Fix duplicated register redirect in netlify.toml"""
path = "/Users/sebastianflorez/Documents/agrotech-digital/agrotech-client-frontend/netlify.toml"

with open(path, "r") as f:
    content = f.read()

# Remove the duplicate
duplicate = """# 3b. Register
[[redirects]]
  from = "/register"
  to = "/templates/authentication/register.html"
  status = 200

# 3b. Register
[[redirects]]
  from = "/register"
  to = "/templates/authentication/register.html"
  status = 200"""

single = """# 3b. Register
[[redirects]]
  from = "/register"
  to = "/templates/authentication/register.html"
  status = 200"""

content = content.replace(duplicate, single)

with open(path, "w") as f:
    f.write(content)

print("✅ Duplicado eliminado de netlify.toml")
