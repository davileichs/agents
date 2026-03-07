import os
import logging
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw
from legacy.core.services.final_fantasy_api import FinalFantasyAPI
from legacy.core.tools.ffxiv import FFXIVUtils

logger = logging.getLogger(__name__)

class FFXIVMapManager:
    def __init__(self):
        self.ff = FFXIVUtils()
    
    async def get_map(self, location_name: str, mark_coordinates: bool = False, 
                      x_coordinate: Optional[float] = None, y_coordinate: Optional[float] = None) -> Dict[str, Any]:
        try:
            if mark_coordinates:
                if x_coordinate is None or y_coordinate is None:
                    return {"success": False, "error": "X and Y coordinates are required when mark_coordinates is true"}
                if not isinstance(x_coordinate, (int, float)) or not isinstance(y_coordinate, (int, float)):
                    return {"success": False, "error": "Coordinates must be valid numbers"}
            
            place_results = await self.ff.get_place_name(location_name)
            
            if not place_results:
                return {"success": False, "message": f"No location found with name: {location_name}", "location_name": location_name}
            
            place_info = place_results[0]
            territory = place_info.get('territory')
            index = place_info.get('index')
            size_factor = place_info.get('size_factor', 100)
            offset_x = place_info.get('offset_x', 0)
            offset_y = place_info.get('offset_y', 0)
            
            if not territory or not index:
                return {"success": False, "message": f"Invalid place data for location: {location_name}", "location_name": location_name}
            
            original_map_filename = f"{territory}_{index}.jpg"
            original_map_exists = self._check_map_exists(original_map_filename)
            
            if original_map_exists:
                map_filename = original_map_filename
                map_dlstats_url = self._get_map_dlstats_url(map_filename)
            else:
                map_filename = await self.ff.get_map_image(territory, index)
                if not map_filename:
                    return {"success": False, "message": f"Failed to retrieve map for: {location_name}", "location_name": location_name}
                map_dlstats_url = self._get_map_dlstats_url(map_filename)
            
            if mark_coordinates:
                marked_filename = await self._mark_coordinates_on_map(map_filename, x_coordinate, y_coordinate,
                                                                   size_factor, offset_x, offset_y)
                if marked_filename:
                    marked_dlstats_url = self._get_map_dlstats_url(marked_filename)
                    return {
                        "success": True,
                        "message": f"Map retrieved and coordinates marked for: {location_name}",
                        "location_name": location_name,
                        "map_filename": marked_filename,
                        "map_url": marked_dlstats_url,
                        "coordinates_marked": True,
                        "x": x_coordinate,
                        "y": y_coordinate
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Map retrieved but failed to mark coordinates for: {location_name}",
                        "location_name": location_name,
                        "map_filename": map_filename,
                        "map_url": map_dlstats_url,
                        "coordinates_marked": False
                    }
            else:
                return {
                    "success": True,
                    "message": f"Map retrieved for: {location_name}",
                    "location_name": location_name,
                    "map_filename": map_filename,
                    "map_url": map_dlstats_url,
                    "coordinates_marked": False
                }
                
        except Exception as e:
            return {"success": False, "error": str(e), "location_name": location_name}

    async def _mark_coordinates_on_map(self, map_filename: str, x: float, y: float, 
                                     size_factor: float, offset_x: float, offset_y: float) -> Optional[str]:
        try:
            folder = os.path.join(self.ff.main_folder, 'maps')
            filepath = os.path.join(folder, map_filename)
            
            if not os.path.exists(filepath):
                return None
            
            with Image.open(filepath) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                width, height = img.size

                pixel_x, pixel_y = self._convert_ffxiv_coordinates_to_pixels(x, y, width, height, 
                                                                          size_factor, offset_x, offset_y)
                
                marked_img = img.copy()
                draw = ImageDraw.Draw(marked_img)
                
                circle_radius = max(16, min(width, height) // 128)
                
                draw.ellipse([pixel_x - circle_radius - 4, pixel_y - circle_radius - 4,
                              pixel_x + circle_radius + 4, pixel_y + circle_radius + 4], outline='black', width=7)
                draw.ellipse([pixel_x - circle_radius, pixel_y - circle_radius,
                              pixel_x + circle_radius, pixel_y + circle_radius], outline='red', width=5)
                
                crosshair_size = circle_radius * 2
                draw.line([pixel_x - crosshair_size - 2, pixel_y, pixel_x + crosshair_size + 2, pixel_y], fill='black', width=6)
                draw.line([pixel_x, pixel_y - crosshair_size - 2, pixel_x, pixel_y + crosshair_size + 2], fill='black', width=6)
                draw.line([pixel_x - crosshair_size, pixel_y, pixel_x + crosshair_size, pixel_y], fill='red', width=4)
                draw.line([pixel_x, pixel_y - crosshair_size, pixel_x, pixel_y + crosshair_size], fill='red', width=4)
                
                x_formatted = f"{x:.1f}"
                y_formatted = f"{y:.1f}"
                name_without_ext = os.path.splitext(map_filename)[0]
                marked_filename = f"marked_{name_without_ext}_x{x_formatted}_y{y_formatted}.jpg"
                marked_filepath = os.path.join(folder, marked_filename)
                marked_img.save(marked_filepath, 'JPEG', quality=95)
                
                return marked_filename
        except Exception:
            return None
    
    def _convert_ffxiv_coordinates_to_pixels(self, x: float, y: float, width: int, height: int, 
                                           size_factor: float, offset_x: float, offset_y: float) -> tuple[int, int]:
        MAP_SIZE = 2048
        scale = MAP_SIZE / size_factor
        pixel_x = (x - offset_x) * scale + MAP_SIZE / 2
        pixel_y = (y - offset_y) * scale + MAP_SIZE / 2
        pixel_x = max(0, min(pixel_x, width - 1))
        pixel_y = max(0, min(pixel_y, height - 1))
        return pixel_x, pixel_y
    
    def _get_map_dlstats_url(self, filename: str) -> str:
        folder = "maps"
        return f"{self.ff.dlstats}/{folder}/{filename}"
    
    def _check_map_exists(self, filename: str) -> bool:
        filepath = os.path.join(self.ff.main_folder, 'maps', filename)
        return os.path.exists(filepath)

_map_mgr = FFXIVMapManager()

async def ffxiv_map(**kwargs) -> Dict[str, Any]:
    """Retrieve map images for FFXIV locations, optionally with coordinate markers."""
    location_name: str = kwargs.get("location_name", "")
    mark_coordinates: bool = kwargs.get("mark_coordinates", False)
    x_coordinate: Optional[float] = kwargs.get("x_coordinate")
    y_coordinate: Optional[float] = kwargs.get("y_coordinate")
    
    return await _map_mgr.get_map(location_name, mark_coordinates, x_coordinate, y_coordinate)
