import logging
from typing import Dict, Any, Optional
from sqlalchemy import select
from app.services.database import AsyncSessionLocal
from app.models.token import Token

logger = logging.getLogger(__name__)

async def manage_ktps_token(action: str, user_id: str, token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Manage the KTPS token for a specific user in the database."""
    service = "ktps"
    
    async with AsyncSessionLocal() as session:
        try:
            if action == "add" or action == "update":
                if not token:
                    return {"success": False, "error": "Token is required for add or update action."}
                
                # Check if exists
                stmt = select(Token).where(Token.user_id == user_id, Token.service == service)
                result = await session.execute(stmt)
                existing_token = result.scalar_one_or_none()
                
                if existing_token:
                    existing_token.token = token
                    message = "Token updated successfully."
                else:
                    new_token = Token(user_id=user_id, service=service, token=token)
                    session.add(new_token)
                    message = "Token added successfully."
                    
                await session.commit()
                return {"success": True, "message": message}
                
            elif action == "delete":
                stmt = select(Token).where(Token.user_id == user_id, Token.service == service)
                result = await session.execute(stmt)
                existing_token = result.scalar_one_or_none()
                
                if existing_token:
                    await session.delete(existing_token)
                    await session.commit()
                    return {"success": True, "message": "Token deleted successfully."}
                else:
                    return {"success": False, "error": "Token not found."}
                    
            elif action == "get":
                stmt = select(Token).where(Token.user_id == user_id, Token.service == service)
                result = await session.execute(stmt)
                existing_token = result.scalar_one_or_none()
                
                if existing_token:
                    return {"success": True, "token": existing_token.token}
                else:
                    return {"success": False, "error": "Token not found."}
                    
            else:
                return {"success": False, "error": f"Invalid action: {action}. Use 'add', 'update', 'delete', or 'get'."}
                
        except Exception as e:
            await session.rollback()
            logger.error(f"Error managing ktps token: {str(e)}")
            return {"success": False, "error": str(e)}
