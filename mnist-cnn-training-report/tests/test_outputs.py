import os
import re
import base64
from html.parser import HTMLParser


class HTMLImageExtractor(HTMLParser):
    """Extract base64 images and text content from HTML."""
    def __init__(self):
        super().__init__()
        self.base64_images = []
        self.text_content = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            for attr, value in attrs:
                if attr == 'src' and value.startswith('data:image'):
                    self.base64_images.append(value)
        elif tag == 'title':
            self.in_title = True

    def handle_data(self, data):
        stripped = data.strip()
        if stripped:
            self.text_content.append(stripped)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False


def test_html_file_exists():
    """Test that the HTML report file exists."""
    assert os.path.exists('/app/mnist_report.html'), "HTML report file not found at /app/mnist_report.html"


def test_html_file_not_empty():
    """Test that the HTML file is not empty."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read()
    assert len(content) > 1000, "HTML file is too small or empty"


def test_html_valid_structure():
    """Test that the HTML has valid basic structure."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read()

    # Check for HTML5 doctype
    assert '<!DOCTYPE html>' in content or '<!doctype html>' in content.lower(), "Missing HTML5 doctype"

    # Check for essential HTML tags
    assert '<html' in content.lower(), "Missing <html> tag"
    assert '<head>' in content.lower() or '<head ' in content.lower(), "Missing <head> tag"
    assert '<body>' in content.lower() or '<body ' in content.lower(), "Missing <body> tag"
    assert '</html>' in content.lower(), "Missing closing </html> tag"


def test_html_contains_base64_images():
    """Test that HTML contains embedded base64 images (no external files)."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read()

    parser = HTMLImageExtractor()
    parser.feed(content)

    # Should have at least 4 base64 images: loss plot, accuracy plot, confusion matrix, sample predictions
    assert len(parser.base64_images) >= 4, f"Expected at least 4 base64 images, found {len(parser.base64_images)}"

    # Verify all images are base64 encoded
    for img_src in parser.base64_images:
        assert img_src.startswith('data:image'), "Image is not base64 encoded"
        assert 'base64,' in img_src, "Image does not contain base64 data"


def test_no_external_dependencies():
    """Test that HTML has no external file references or broken links."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read()

    # Check for external image references (should not exist)
    external_patterns = [
        r'<img[^>]+src=["\'](?!data:)[^"\']+\.(png|jpg|jpeg|gif|svg)',
        r'<link[^>]+href=["\'](?!data:)[^"\']+\.css',
        r'<script[^>]+src=["\'](?!data:)[^"\']+\.js'
    ]

    for pattern in external_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        assert len(matches) == 0, f"Found external dependencies: {matches}"


def test_html_contains_test_accuracy():
    """Test that HTML contains test accuracy metric."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read()

    # Look for accuracy percentage (should be between 90-100% for MNIST)
    accuracy_patterns = [
        r'(\d+\.\d+)%',
        r'accuracy[:\s]+(\d+\.\d+)',
        r'test[_\s]+accuracy[:\s]+(\d+\.\d+)'
    ]

    found_accuracy = False
    for pattern in accuracy_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            accuracy = float(match)
            if 90.0 <= accuracy <= 100.0:
                found_accuracy = True
                break
        if found_accuracy:
            break

    assert found_accuracy, "Could not find valid test accuracy (90-100%) in HTML"


def test_html_contains_training_metrics_section():
    """Test that HTML contains training metrics section."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read().lower()

    # Check for training-related keywords
    assert 'training' in content or 'train' in content, "Missing training metrics section"
    assert 'loss' in content, "Missing loss information"
    assert 'accuracy' in content, "Missing accuracy information"


def test_html_contains_confusion_matrix_section():
    """Test that HTML contains confusion matrix section."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read().lower()

    assert 'confusion' in content and 'matrix' in content, "Missing confusion matrix section"


def test_html_contains_sample_predictions_section():
    """Test that HTML contains sample predictions section."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read().lower()

    # Check for sample/prediction keywords
    assert 'sample' in content or 'prediction' in content or 'predict' in content, \
        "Missing sample predictions section"


def test_html_contains_model_architecture():
    """Test that HTML contains model architecture or technical details."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read().lower()

    # Check for architecture/model keywords
    architecture_keywords = ['architecture', 'model', 'layer', 'conv', 'dense', 'parameter']
    found = any(keyword in content for keyword in architecture_keywords)

    assert found, "Missing model architecture or technical details"


def test_html_contains_training_parameters():
    """Test that HTML mentions training parameters like epochs."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read().lower()

    # Should mention 5 epochs as specified in requirements
    assert 'epoch' in content, "Missing epoch information"
    assert '5' in content, "Missing reference to 5 epochs"


def test_base64_images_are_valid():
    """Test that base64 images can be decoded successfully."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read()

    parser = HTMLImageExtractor()
    parser.feed(content)

    for img_src in parser.base64_images:
        # Extract base64 data
        if 'base64,' in img_src:
            base64_data = img_src.split('base64,')[1]
            try:
                # Try to decode base64
                decoded = base64.b64decode(base64_data)
                assert len(decoded) > 100, "Decoded image is too small"
            except Exception as e:
                assert False, f"Failed to decode base64 image: {e}"


def test_html_self_contained():
    """Test that HTML is truly self-contained with no external URLs."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read()

    # Check for http:// or https:// URLs (except in comments or meta tags)
    # Remove comments first
    content_no_comments = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

    # Look for external URLs in src, href attributes
    external_urls = re.findall(r'(?:src|href)=["\']https?://', content_no_comments, re.IGNORECASE)

    assert len(external_urls) == 0, f"Found external URLs: {external_urls}"


def test_html_contains_digit_labels():
    """Test that HTML references digit labels 0-9 (for confusion matrix)."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read()

    # Should contain references to digits 0-9 in context of labels/predictions
    digit_count = sum(1 for i in range(10) if str(i) in content)

    assert digit_count >= 8, "Missing sufficient digit label references (0-9)"


def test_html_file_size_reasonable():
    """Test that HTML file size is reasonable (not suspiciously small or huge)."""
    file_size = os.path.getsize('/app/mnist_report.html')

    # Should be at least 100KB (with base64 images) but less than 50MB
    assert file_size > 100_000, f"HTML file too small ({file_size} bytes), likely missing images"
    assert file_size < 50_000_000, f"HTML file too large ({file_size} bytes)"


def test_html_contains_validation_metrics():
    """Test that HTML mentions validation metrics (validation split was used)."""
    with open('/app/mnist_report.html', 'r') as f:
        content = f.read().lower()

    # Should mention validation since 20% validation split is required
    assert 'validation' in content or 'val' in content, "Missing validation metrics"
