from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from mysql_app import crud, schemas
from mysql_app.schemas import StandardResponse
from utils.dependencies import get_db
from utils.authentication import verify_api_token
from base_logger import get_logger


logger = get_logger(__name__)
china_router = APIRouter(tags=["Git Repository"], prefix="/git-repository")
global_router = APIRouter(tags=["Git Repository"], prefix="/git-repository")
fujian_router = APIRouter(tags=["Git Repository"], prefix="/git-repository")


@china_router.get("/all", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@global_router.get("/all", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@fujian_router.get("/all", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def get_all_git_repositories(db: Session = Depends(get_db)) -> StandardResponse:
    """
    Get all git repositories from database. **This endpoint requires API token verification**
    
    :param db: Database session
    :return: A list of git repository objects
    """
    repositories = crud.get_all_git_repositories(db)
    repository_dicts = [
        schemas.GitRepository.model_validate(repo.to_dict()).model_dump()
        for repo in repositories
    ]
    return StandardResponse(data=repository_dicts, message="Successfully fetched all git repositories")


@china_router.post("/create", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@global_router.post("/create", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@fujian_router.post("/create", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def create_git_repository(repository: schemas.GitRepositoryCreate, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Create a new git repository record. **This endpoint requires API token verification**
    
    :param repository: Git repository object to create
    :param db: Database session
    :return: StandardResponse object with created repository data
    """
    # Check if repository with the same name already exists
    existing = crud.get_git_repository_by_name(db, repository.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Repository with name '{repository.name}' already exists")
    
    created_repository = crud.create_git_repository(db, repository)
    return StandardResponse(
        data=schemas.GitRepository.model_validate(created_repository.to_dict()).model_dump(),
        message="Git repository created successfully"
    )


@china_router.put("/update", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@global_router.put("/update", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@fujian_router.put("/update", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def update_git_repository(
    repository: schemas.GitRepositoryUpdate,
    repo_id: Optional[int] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Update a git repository by ID or name. **This endpoint requires API token verification**
    
    :param repository: Git repository update data
    :param repo_id: Repository ID (optional)
    :param name: Repository name (optional)
    :param db: Database session
    :return: StandardResponse object with updated repository data
    """
    if not repo_id and not name:
        raise HTTPException(status_code=400, detail="Either repo_id or name must be provided")
    
    try:
        if repo_id:
            updated_repository = crud.update_git_repository(db, repo_id, repository)
        else:
            updated_repository = crud.update_git_repository_by_name(db, name, repository)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not updated_repository:
        raise HTTPException(status_code=404, detail="Git repository not found")
    
    return StandardResponse(
        data=schemas.GitRepository.model_validate(updated_repository.to_dict()).model_dump(),
        message="Git repository updated successfully"
    )


@china_router.delete("/delete", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@global_router.delete("/delete", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@fujian_router.delete("/delete", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def delete_git_repository(
    repo_id: Optional[int] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Delete a git repository by ID or name. **This endpoint requires API token verification**
    
    :param repo_id: Repository ID (optional)
    :param name: Repository name (optional)
    :param db: Database session
    :return: StandardResponse object confirming deletion
    """
    if not repo_id and not name:
        raise HTTPException(status_code=400, detail="Either repo_id or name must be provided")
    
    if repo_id:
        success = crud.delete_git_repository(db, repo_id)
    else:
        success = crud.delete_git_repository_by_name(db, name)
    
    if not success:
        raise HTTPException(status_code=404, detail="Git repository not found")
    
    return StandardResponse(
        data={"success": True},
        message="Git repository deleted successfully"
    )
