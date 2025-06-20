import unittest
from src.processors.text_parser import TextParser

class TestTextParser(unittest.TestCase):
    def test_parse(self):
        parser = TextParser()
        text = "Matrícula: 2411367\nNombre: Juan\nApellido Paterno: Perez\nApellido Materno: Lopez"
        data = parser.parse(text)
        self.assertEqual(data['alu_matricula'], '2411367')
        self.assertEqual(data['alu_nombre'], 'Juan')
        self.assertEqual(data['alu_paterno'], 'Perez')
        self.assertEqual(data['alu_materno'], 'Lopez')

if __name__ == '__main__':
    unittest.main()