#!/usr/bin/env python3
"""Unit tests for recipe matching logic."""

import unittest
from match_recipes import (
    normalize, 
    match_score, 
    find_matching_deals,
    SYNONYMS,
    IGNORE_WORDS,
    FALSE_MATCHES
)


class TestNormalize(unittest.TestCase):
    """Test the normalize function."""
    
    def test_lowercase(self):
        self.assertEqual(normalize('KYCKLING'), 'kyckling')
    
    def test_remove_diacritics(self):
        self.assertEqual(normalize('Bröd'), 'brod')
        self.assertEqual(normalize('Ägg'), 'agg')
        self.assertEqual(normalize('Kött'), 'kott')
    
    def test_remove_prefixes(self):
        self.assertEqual(normalize('Farsk lax'), 'lax')
        self.assertEqual(normalize('Fryst broccoli'), 'broccoli')
        self.assertEqual(normalize('Ekologisk mjölk'), 'mjolk')
        self.assertEqual(normalize('Svensk potatis'), 'potatis')
    
    def test_remove_suffixes(self):
        self.assertEqual(normalize('Kyckling farsk'), 'kyckling')
        self.assertEqual(normalize('Lax fryst'), 'lax')


class TestMatchScore(unittest.TestCase):
    """Test the match_score function."""
    
    def test_exact_match(self):
        """Exact matches should return 1.0"""
        self.assertEqual(match_score('kyckling', 'kyckling'), 1.0)
        self.assertEqual(match_score('Kyckling', 'kyckling'), 1.0)
    
    def test_ignore_words(self):
        """Common ingredients should be ignored"""
        for word in IGNORE_WORDS:
            self.assertEqual(match_score(word, word), 0.0)
    
    def test_false_matches(self):
        """False match pairs should return 0.0"""
        # Test with actual patterns from FALSE_MATCHES
        # match_score(deal_name, ingredient) - so deal is first param
        self.assertEqual(match_score('riskakor', 'ris'), 0.0)
        self.assertEqual(match_score('palagg', 'agg'), 0.0)
        self.assertEqual(match_score('strobrod', 'brod'), 0.0)
    
    def test_substring_match(self):
        """Substrings should score 0.9"""
        score = match_score('kycklingfilé', 'kyckling')
        self.assertGreaterEqual(score, 0.8)
    
    def test_synonym_match(self):
        """Synonyms should score high"""
        # Test kyckling synonyms
        score = match_score('kycklingfilé', 'kyckling')
        self.assertGreater(score, 0.7)
        
        # Test ost synonyms
        score = match_score('parmesan', 'ost')
        self.assertGreater(score, 0.7)
    
    def test_no_match(self):
        """Completely different items should score 0.0"""
        self.assertEqual(match_score('banan', 'kyckling'), 0.0)
        self.assertEqual(match_score('mjölk', 'tomat'), 0.0)
    
    def test_word_overlap(self):
        """Items with common significant words should score > 0.5"""
        score = match_score('riven ost', 'ost parmesan')
        self.assertGreater(score, 0.5)


class TestFindMatchingDeals(unittest.TestCase):
    """Test the find_matching_deals function."""
    
    def setUp(self):
        """Create sample deals for testing."""
        self.deals = [
            {'name': 'Kycklingfilé ICA', 'price': '99:-', 'store': 'ICA'},
            {'name': 'Laxfilé färsk', 'price': '129:-', 'store': 'Coop'},
            {'name': 'Riven ost', 'price': '39:-', 'store': 'Willys'},
            {'name': 'Bananer', 'price': '19:-', 'store': 'ICA'},
            {'name': 'Helt orelaterad produkt', 'price': '50:-', 'store': 'ICA'},
        ]
    
    def test_find_exact_match(self):
        """Should find exact matches"""
        matches = find_matching_deals('kyckling', self.deals, threshold=0.6)
        self.assertGreater(len(matches), 0)
        self.assertIn('kyckling', normalize(matches[0]['deal']['name']))
    
    def test_find_multiple_matches(self):
        """Should find multiple matching stores for same ingredient"""
        # Add multiple stores with chicken
        multi_deals = self.deals + [
            {'name': 'Kyckling ICA', 'price': '89:-', 'store': 'Coop'},
        ]
        matches = find_matching_deals('kyckling', multi_deals, threshold=0.6)
        stores = {m['deal']['store'] for m in matches}
        self.assertGreater(len(stores), 1)
    
    def test_no_matches_below_threshold(self):
        """Should return empty list when no deals match"""
        matches = find_matching_deals('exotisk frukt', self.deals, threshold=0.9)
        self.assertEqual(len(matches), 0)
    
    def test_threshold_filtering(self):
        """Higher thresholds should return fewer matches"""
        low_threshold = find_matching_deals('ost', self.deals, threshold=0.5)
        high_threshold = find_matching_deals('ost', self.deals, threshold=0.9)
        self.assertGreaterEqual(len(low_threshold), len(high_threshold))
    
    def test_sorted_by_score(self):
        """Matches should be sorted by score descending"""
        matches = find_matching_deals('kyckling', self.deals, threshold=0.5)
        if len(matches) > 1:
            for i in range(len(matches) - 1):
                self.assertGreaterEqual(matches[i]['score'], matches[i + 1]['score'])


class TestDataStructures(unittest.TestCase):
    """Test that data structures are well-formed."""
    
    def test_synonyms_structure(self):
        """SYNONYMS should be dict with string keys and list values"""
        self.assertIsInstance(SYNONYMS, dict)
        for key, value in SYNONYMS.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, list)
            for item in value:
                self.assertIsInstance(item, str)
    
    def test_ignore_words_structure(self):
        """IGNORE_WORDS should be a set of strings"""
        self.assertIsInstance(IGNORE_WORDS, set)
        for word in IGNORE_WORDS:
            self.assertIsInstance(word, str)
    
    def test_false_matches_structure(self):
        """FALSE_MATCHES should be list of tuples"""
        self.assertIsInstance(FALSE_MATCHES, list)
        for pair in FALSE_MATCHES:
            self.assertIsInstance(pair, tuple)
            self.assertEqual(len(pair), 2)
            self.assertIsInstance(pair[0], str)
            self.assertIsInstance(pair[1], str)


if __name__ == '__main__':
    unittest.main()
