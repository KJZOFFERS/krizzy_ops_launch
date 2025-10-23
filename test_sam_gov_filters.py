"""
Tests for SAM.gov and GovCon filtering logic.
"""
import pytest
from datetime import datetime, timedelta
from govcon_subtrap_engine import GovConProcessor


class TestGovConProcessor:
    """Test GovConProcessor filtering and processing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.dict('os.environ', {
            'SAM_SEARCH_API': 'https://api.sam.gov/v1/search',
            'SAM_API_KEY': 'test_key',
            'NAICS_WHITELIST': '541511,541512,541519',
            'UEI': 'TEST123456789',
            'CAGE_CODE': 'TEST1'
        }):
            self.processor = GovConProcessor()
    
    def test_naics_whitelist_loading(self):
        """Test NAICS whitelist loading from environment."""
        assert '541511' in self.processor.naics_whitelist
        assert '541512' in self.processor.naics_whitelist
        assert '541519' in self.processor.naics_whitelist
    
    def test_filter_opportunity_combined_synopsis(self):
        """Test filtering for Combined Synopsis/Solicitation."""
        opportunity = {
            'type': 'Combined Synopsis/Solicitation',
            'responseDate': (datetime.now() + timedelta(days=3)).isoformat() + 'Z',
            'naicsCode': '541511',
            'officers': [{'email': 'test@agency.gov'}]
        }
        
        assert self.processor._filter_opportunity(opportunity) is True
    
    def test_filter_opportunity_solicitation(self):
        """Test filtering for Solicitation."""
        opportunity = {
            'type': 'Solicitation',
            'responseDate': (datetime.now() + timedelta(days=5)).isoformat() + 'Z',
            'naicsCode': '541512',
            'officers': [{'email': 'test@agency.gov'}]
        }
        
        assert self.processor._filter_opportunity(opportunity) is True
    
    def test_filter_opportunity_wrong_type(self):
        """Test filtering out wrong notice type."""
        opportunity = {
            'type': 'Award Notice',
            'responseDate': (datetime.now() + timedelta(days=3)).isoformat() + 'Z',
            'naicsCode': '541511',
            'officers': [{'email': 'test@agency.gov'}]
        }
        
        assert self.processor._filter_opportunity(opportunity) is False
    
    def test_filter_opportunity_due_date_too_far(self):
        """Test filtering out opportunities due too far in future."""
        opportunity = {
            'type': 'Combined Synopsis/Solicitation',
            'responseDate': (datetime.now() + timedelta(days=10)).isoformat() + 'Z',
            'naicsCode': '541511',
            'officers': [{'email': 'test@agency.gov'}]
        }
        
        assert self.processor._filter_opportunity(opportunity) is False
    
    def test_filter_opportunity_due_date_past(self):
        """Test filtering out past due opportunities."""
        opportunity = {
            'type': 'Combined Synopsis/Solicitation',
            'responseDate': (datetime.now() - timedelta(days=1)).isoformat() + 'Z',
            'naicsCode': '541511',
            'officers': [{'email': 'test@agency.gov'}]
        }
        
        assert self.processor._filter_opportunity(opportunity) is False
    
    def test_filter_opportunity_naics_not_whitelisted(self):
        """Test filtering out opportunities with non-whitelisted NAICS."""
        opportunity = {
            'type': 'Combined Synopsis/Solicitation',
            'responseDate': (datetime.now() + timedelta(days=3)).isoformat() + 'Z',
            'naicsCode': '999999',  # Not in whitelist
            'officers': [{'email': 'test@agency.gov'}]
        }
        
        assert self.processor._filter_opportunity(opportunity) is False
    
    def test_filter_opportunity_no_contact(self):
        """Test filtering out opportunities without contact information."""
        opportunity = {
            'type': 'Combined Synopsis/Solicitation',
            'responseDate': (datetime.now() + timedelta(days=3)).isoformat() + 'Z',
            'naicsCode': '541511',
            'officers': []  # No officers
        }
        
        assert self.processor._filter_opportunity(opportunity) is False
    
    def test_filter_opportunity_no_email(self):
        """Test filtering out opportunities without email."""
        opportunity = {
            'type': 'Combined Synopsis/Solicitation',
            'responseDate': (datetime.now() + timedelta(days=3)).isoformat() + 'Z',
            'naicsCode': '541511',
            'officers': [{'name': 'John Doe'}]  # No email
        }
        
        assert self.processor._filter_opportunity(opportunity) is False
    
    def test_enrich_opportunity(self):
        """Test opportunity enrichment."""
        opportunity = {
            'solicitationNumber': 'TEST-2024-001',
            'title': 'Test Solicitation',
            'naicsCode': '541511',
            'responseDate': (datetime.now() + timedelta(days=3)).isoformat() + 'Z',
            'officers': [{
                'fullName': 'John Doe',
                'email': 'john.doe@agency.gov',
                'phone': '555-1234'
            }],
            'department': 'Department of Test',
            'subTier': 'Test Agency',
            'type': 'Combined Synopsis/Solicitation',
            'uiLink': 'https://sam.gov/test',
            'description': 'Test description',
            'awardAmount': '100000'
        }
        
        enriched = self.processor._enrich_opportunity(opportunity)
        
        assert enriched['Solicitation #'] == 'TEST-2024-001'
        assert enriched['Title'] == 'Test Solicitation'
        assert enriched['NAICS'] == '541511'
        assert enriched['Officer'] == 'John Doe'
        assert enriched['Email'] == 'john.doe@agency.gov'
        assert enriched['Phone'] == '555-1234'
        assert enriched['Agency'] == 'Department of Test'
        assert enriched['Sub_Agency'] == 'Test Agency'
        assert enriched['Status'] == 'Combined Synopsis/Solicitation'
        assert enriched['Link'] == 'https://sam.gov/test'
        assert enriched['Source'] == 'SAM.gov'
        assert 'source_id' in enriched
        assert 'Bid_Pack_JSON' in enriched
        
        # Check bid pack JSON
        bid_pack = json.loads(enriched['Bid_Pack_JSON'])
        assert bid_pack['solicitation_number'] == 'TEST-2024-001'
        assert bid_pack['uei'] == 'TEST123456789'
        assert bid_pack['cage_code'] == 'TEST1'
        assert bid_pack['days_until_due'] == 3
    
    def test_deduplicate_opportunities(self):
        """Test opportunity deduplication."""
        new_opportunities = [
            {'Solicitation #': 'TEST-001', 'Title': 'Test 1'},
            {'Solicitation #': 'TEST-002', 'Title': 'Test 2'},
            {'Solicitation #': 'TEST-003', 'Title': 'Test 3'}
        ]
        
        # Mock existing opportunities
        with patch.object(self.processor, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = [
                {'fields': {'Solicitation #': 'TEST-001'}},
                {'fields': {'Solicitation #': 'TEST-004'}}
            ]
            
            unique = self.processor._deduplicate_opportunities(new_opportunities)
            
            assert len(unique) == 2
            assert unique[0]['Solicitation #'] == 'TEST-002'
            assert unique[1]['Solicitation #'] == 'TEST-003'
    
    def test_empty_naics_whitelist(self):
        """Test behavior with empty NAICS whitelist."""
        with patch.dict('os.environ', {
            'SAM_SEARCH_API': 'https://api.sam.gov/v1/search',
            'SAM_API_KEY': 'test_key',
            'NAICS_WHITELIST': '',  # Empty whitelist
            'UEI': 'TEST123456789',
            'CAGE_CODE': 'TEST1'
        }):
            processor = GovConProcessor()
            
            opportunity = {
                'type': 'Combined Synopsis/Solicitation',
                'responseDate': (datetime.now() + timedelta(days=3)).isoformat() + 'Z',
                'naicsCode': '999999',  # Any NAICS should pass
                'officers': [{'email': 'test@agency.gov'}]
            }
            
            assert processor._filter_opportunity(opportunity) is True