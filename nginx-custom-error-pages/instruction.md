Configure a production-ready Nginx web server on Ubuntu with custom error pages for HTTP errors 404, 500, 502, 503, and 504.

## Technical Requirements

- Install Nginx via apt
- Nginx must be running after setup is complete
- Nginx configuration must pass `nginx -t` syntax check

## Custom Error Pages

Create custom HTML error pages at the following paths:

- `/var/www/html/errors/404.html`
- `/var/www/html/errors/500.html`
- `/var/www/html/errors/502.html`
- `/var/www/html/errors/503.html`
- `/var/www/html/errors/504.html`

Each error page must:

1. Be a valid HTML file with `<!DOCTYPE html>`, `<html>`, `<head>`, and `<body>` tags.
2. Include a `<title>` tag containing the corresponding error code (e.g., `404`).
3. Display the error code in an `<h1>` tag (e.g., the text `404` must appear inside an `<h1>`).
4. Include a descriptive message visible on the page that is relevant to the error type (e.g., "Page Not Found" for 404, "Internal Server Error" for 500).
5. Include a link (`<a>` tag) with `href="/"` to navigate back to the home page.
6. Include at least one `<style>` block with CSS styling (inline in the HTML file).

## Nginx Configuration

Modify the Nginx site configuration (the default site config under `/etc/nginx/sites-available/` or `/etc/nginx/conf.d/`) so that:

1. A `server` block listens on port `80`.
2. The `root` directive points to `/var/www/html`.
3. For each of the five error codes (404, 500, 502, 503, 504), an `error_page` directive maps the code to the corresponding file under `/errors/` (e.g., `error_page 404 /errors/404.html;`).
4. A `location` block for `/errors/` is defined with `internal;` so that error pages are not directly browsable.

## Verification

- `curl -s -o /dev/null -w "%{http_code}" http://localhost/nonexistent-page` must return status code `404`, and `curl -s http://localhost/nonexistent-page` must contain the custom 404 page content (the `<h1>` with `404` and the back-to-home link).
- Requesting `http://localhost/errors/404.html` directly must NOT serve the file (because of the `internal` directive).
