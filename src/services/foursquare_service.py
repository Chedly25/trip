"""
Foursquare Places API integration for restaurants and activities.
Free tier: 1000 requests/day
"""
import os
import asyncio
import aiohttp
from typing import List, Dict, Optional
import structlog
from ..core.models import Coordinates

logger = structlog.get_logger(__name__)


class FoursquareService:
    """Service for finding restaurants and activities using Foursquare Places API."""
    
    def __init__(self):
        self.api_key = os.getenv('FOURSQUARE_API_KEY')
        self.base_url = "https://places-api.foursquare.com/places"
        self.session = None
        
        if not self.api_key:
            logger.warning("Foursquare API key not configured - using fallback data")
    
    async def find_restaurants(self, coordinates: Coordinates, city_name: str, limit: int = 10) -> List[Dict]:
        """Find top restaurants near the given coordinates."""
        if not self.api_key:
            return self._get_fallback_restaurants(city_name, limit)
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/search"
            params = {
                'll': f"{coordinates.latitude},{coordinates.longitude}",
                'categories': '13000',  # Food & Drink category
                'limit': limit,
                'sort': 'RATING',
                'fields': 'name,rating,price,location,categories,photos,hours,website'
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json',
                'X-Places-Api-Version': '2025-06-17'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_restaurants(data.get('results', []))
                else:
                    error_text = await response.text()
                    logger.error(f"Foursquare API error: {response.status} - {error_text}")
                    return self._get_fallback_restaurants(city_name, limit)
                    
        except Exception as e:
            logger.error(f"Restaurant search error: {e}")
            return self._get_fallback_restaurants(city_name, limit)
        finally:
            if self.session:
                await self.session.close()
                self.session = None
    
    async def find_activities(self, coordinates: Coordinates, city_name: str, limit: int = 10) -> List[Dict]:
        """Find top activities and attractions near the given coordinates."""
        if not self.api_key:
            return self._get_fallback_activities(city_name, limit)
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/search"
            params = {
                'll': f"{coordinates.latitude},{coordinates.longitude}",
                'categories': '10000,12000,16000',  # Arts & Entertainment, Events, Travel & Transport
                'limit': limit,
                'sort': 'RATING',
                'fields': 'name,rating,price,location,categories,photos,hours,website'
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json',
                'X-Places-Api-Version': '2025-06-17'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_activities(data.get('results', []))
                else:
                    error_text = await response.text()
                    logger.error(f"Foursquare API error: {response.status} - {error_text}")
                    return self._get_fallback_activities(city_name, limit)
                    
        except Exception as e:
            logger.error(f"Activities search error: {e}")
            return self._get_fallback_activities(city_name, limit)
        finally:
            if self.session:
                await self.session.close()
                self.session = None
    
    def _format_restaurants(self, results: List[Dict]) -> List[Dict]:
        """Format Foursquare restaurant data."""
        formatted = []
        for place in results:
            try:
                website_url = place.get('website', '')
                
                formatted.append({
                    'name': place.get('name', 'Unknown Restaurant'),
                    'rating': place.get('rating', 0) / 2,  # Convert from 10-point to 5-point scale
                    'price_level': len(place.get('price', '') or ''),
                    'address': place.get('location', {}).get('formatted_address', ''),
                    'category': 'Restaurant',
                    'cuisine': self._extract_cuisine(place.get('categories', [])),
                    'website': website_url,
                    'url': website_url,  # Add url field for consistency
                    'hours': place.get('hours', {}).get('display', 'Hours not available'),
                    'photo': self._extract_photo(place.get('photos', [])),
                    'source': 'foursquare'
                })
            except Exception as e:
                logger.error(f"Error formatting restaurant: {e}")
                continue
        return formatted
    
    def _format_activities(self, results: List[Dict]) -> List[Dict]:
        """Format Foursquare activity data."""
        formatted = []
        for place in results:
            try:
                website_url = place.get('website', '')
                
                formatted.append({
                    'name': place.get('name', 'Unknown Activity'),
                    'rating': place.get('rating', 0) / 2,  # Convert from 10-point to 5-point scale
                    'price_level': len(place.get('price', '') or ''),
                    'address': place.get('location', {}).get('formatted_address', ''),
                    'category': self._extract_activity_type(place.get('categories', [])),
                    'website': website_url,
                    'url': website_url,  # Add url field for consistency
                    'hours': place.get('hours', {}).get('display', 'Hours not available'),
                    'photo': self._extract_photo(place.get('photos', [])),
                    'source': 'foursquare'
                })
            except Exception as e:
                logger.error(f"Error formatting activity: {e}")
                continue
        return formatted
    
    def _extract_cuisine(self, categories: List[Dict]) -> str:
        """Extract cuisine type from categories."""
        if not categories:
            return 'International'
        
        primary_category = categories[0].get('name', 'Restaurant')
        return primary_category
    
    def _extract_activity_type(self, categories: List[Dict]) -> str:
        """Extract activity type from categories."""
        if not categories:
            return 'Attraction'
        
        primary_category = categories[0].get('name', 'Attraction')
        return primary_category
    
    def _extract_photo(self, photos: List[Dict]) -> str:
        """Extract first photo URL."""
        if not photos:
            return ''
        
        photo = photos[0]
        prefix = photo.get('prefix', '')
        suffix = photo.get('suffix', '')
        if prefix and suffix:
            return f"{prefix}300x300{suffix}"
        return ''
    
    def _get_fallback_restaurants(self, city_name: str, limit: int) -> List[Dict]:
        """Fallback when restaurant API is unavailable - returns empty list to indicate no data."""
        logger.warning(f"Foursquare restaurant service unavailable for {city_name}. No fallback data provided.")
        return []
    
    def _get_fallback_activities(self, city_name: str, limit: int) -> List[Dict]:
        """Fallback when activities API is unavailable - returns empty list to indicate no data."""
        logger.warning(f"Foursquare activities service unavailable for {city_name}. No fallback data provided.")
        return []
    
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()