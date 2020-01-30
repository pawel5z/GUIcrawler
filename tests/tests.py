import unittest
import context
from gui_handling import comaSepToList, parseAttrSpec, parseStartSiteAddress

class textParsingTestCase(unittest.TestCase):
    def testComaSepToList(self):
        self.assertEqual(comaSepToList(''), [])
        self.assertEqual(comaSepToList('div'), ['div'])
        self.assertEqual(comaSepToList('div,'), ['div', ''])
        self.assertEqual(comaSepToList('div,h1'), ['div', 'h1'])
        self.assertEqual(comaSepToList('div,h1,'), ['div', 'h1', ''])
    
    def testParseAttrSpec(self):
        self.assertEqual(parseAttrSpec('href:foo'), {
                                                        'href': ['foo']
                                                    })
        self.assertEqual(parseAttrSpec('href:foo,bar'), {
                                                            'href': ['foo', 'bar']
                                                        })
        self.assertEqual(parseAttrSpec('href:foo,bar\nid:foo'), {
                                                                    'href': ['foo', 'bar'],
                                                                    'id': ['foo']
                                                                })
        self.assertEqual(parseAttrSpec('href:foo,bar\nid:foo,bar'), {
                                                                        'href': ['foo', 'bar'],
                                                                        'id': ['foo', 'bar']
                                                                    })
    def testParseStartSiteAddress(self):
        self.assertEqual(parseStartSiteAddress(''), '')
        self.assertEqual(parseStartSiteAddress('sample/'), 'sample/')
        self.assertEqual(parseStartSiteAddress('sample'), 'sample/')

if __name__ == '__main__':  
    unittest.main()  
