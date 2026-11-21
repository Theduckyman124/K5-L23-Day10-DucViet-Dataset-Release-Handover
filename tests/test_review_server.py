import base64
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import HTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from PIL import Image
from tool.server import handler


class ServerTest(unittest.TestCase):
    def test_upload_persistence_review_and_invalid_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            (root / 'catalog.json').write_text(json.dumps([{'name': 'a'}]))
            server = HTTPServer(('127.0.0.1', 0), handler(root))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def request(path, data=None):
                payload = json.dumps(data).encode() if data else None
                with urlopen(Request(f'http://127.0.0.1:{server.server_port}'+path, data=payload), timeout=5) as response:
                    return response.read()
            try:
                image = io.BytesIO()
                Image.new('RGB', (12, 10), 'red').save(image, format='PNG')
                item = json.loads(request('/api/upload', {'name': 'photo.png', 'data': base64.b64encode(image.getvalue()).decode()}))
                self.assertEqual(item['width'], 12)
                self.assertEqual(len(json.loads(request('/api/images'))), 2)
                self.assertEqual(json.loads((root/'uploads.json').read_text())[0]['index'], item['index'])
                self.assertTrue(request('/assets/'+item['index']+'_original.png').startswith(b'\x89PNG'))
                row = dict(image='a', type='class_swap', verdict='confirmed', reviewer='Tester', note='Test observation of the actual object')
                request('/api/reviews', row)
                row['verdict'] = 'rejected'
                request('/api/reviews', row)
                reviews = json.loads(request('/api/reviews'))
                self.assertEqual(len(reviews), 1)
                self.assertEqual(reviews[0]['verdict'], 'rejected')
                self.assertIn(b'Tester:', request('/api/reviews.csv'))
                with self.assertRaises(HTTPError) as error:
                    request('/api/upload', {'name': 'bad.png', 'data': 'invalid'})
                self.assertEqual(error.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
