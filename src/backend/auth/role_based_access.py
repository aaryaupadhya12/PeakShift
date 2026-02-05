from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from backend.config import get_connection

router = APIRouter()


class RolePermissions(BaseModel):
    role: str
    permissions: List[str]


def get_db():
    return get_connection()


# Define role permissions
ROLE_PERMISSIONS = {
    'admin': [
        'create_shift',
        'publish_shift',
        'delete_shift',
        'validate_shift',
        'manage_users',
        'view_all_shifts',
        'volunteer_for_shift'
    ],
    'manager': [
        'create_shift',
        'publish_shift',
        'delete_shift',
        'view_all_shifts',
        'volunteer_for_shift'
    ],
    'volunteer': [
        'view_all_shifts',
        'volunteer_for_shift',
        'cancel_volunteer'
    ]
}


@router.get("/roles/{role}/permissions")
def get_role_permissions(role: str):
    """
    Get permissions for a specific role
    - Returns list of allowed actions for the role
    """
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=404, detail="Role not found")

    return {
        "role": role,
        "permissions": ROLE_PERMISSIONS[role]
    }


@router.get("/check-permission")
def check_user_permission(username: str, action: str):
    """
    Check if user has permission for specific action
    - Validates user role
    - Checks if action is allowed for that role
    """
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    ).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = user['role']

    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=403, detail="Invalid role")

    has_permission = action in ROLE_PERMISSIONS[role]

    return {
        "username": username,
        "role": role,
        "action": action,
        "has_permission": has_permission,
        "message": "Permission granted" if has_permission else "Permission denied"
    }


def verify_role_access(required_roles: List[str]):
    """
    Dependency function to verify role-based access
    Usage: @router.post("/endpoint", dependencies=[Depends(verify_role_access(['admin', 'manager']))])
    """
    def role_checker(role: str):
        if role not in required_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        return True
    return role_checker


@router.post("/validate-action")
def validate_user_action(username: str, role: str, action: str):
    """
    Validate if a user can perform an action
    - Used before executing sensitive operations
    """
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=403, detail="Invalid role")

    if action not in ROLE_PERMISSIONS[role]:
        raise HTTPException(
            status_code=403,
            detail=f"User with role '{role}' cannot perform action '{action}'"
        )

    return {
        "valid": True,
        "username": username,
        "role": role,
        "action": action,
        "message": "Action authorized"
    }
