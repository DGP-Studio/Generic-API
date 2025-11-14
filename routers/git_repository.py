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


@china_router.get("/all", response_model=StandardResponse)
@fujian_router.get("/all", response_model=StandardResponse)
async def get_all_git_repositories_cn(name: Optional[str] = None, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Get all git repositories from database (filtered by region=cn), or repositories by name if provided.
    
    :param name: Optional repository name to filter by (returns all repositories with this name)
    :param db: Database session
    :return: A list of git repository objects
    """
    region = "cn"
    if name:
        # Get all repositories by name and region
        repositories = crud.get_git_repositories_by_name(db, name, region)
        if not repositories:
            raise HTTPException(status_code=404, detail=f"No repositories found with name '{name}' and region '{region}'")
        repository_dicts = [
            schemas.GitRepository.model_validate(repo.to_dict()).model_dump()
            for repo in repositories
        ]
        message = f"Successfully fetched {len(repositories)} repository(ies) with name '{name}' in region '{region}'"
    else:
        # Get all repositories for this region
        repositories = crud.get_all_git_repositories(db, region)
        repository_dicts = [
            schemas.GitRepository.model_validate(repo.to_dict()).model_dump()
            for repo in repositories
        ]
        message = f"Successfully fetched all git repositories in region '{region}'"
    return StandardResponse(data=repository_dicts, message=message)


@global_router.get("/all", response_model=StandardResponse)
async def get_all_git_repositories_global(name: Optional[str] = None, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Get all git repositories from database (filtered by region=global), or repositories by name if provided.
    
    :param name: Optional repository name to filter by (returns all repositories with this name)
    :param db: Database session
    :return: A list of git repository objects
    """
    region = "global"
    if name:
        # Get all repositories by name and region
        repositories = crud.get_git_repositories_by_name(db, name, region)
        if not repositories:
            raise HTTPException(status_code=404, detail=f"No repositories found with name '{name}' and region '{region}'")
        repository_dicts = [
            schemas.GitRepository.model_validate(repo.to_dict()).model_dump()
            for repo in repositories
        ]
        message = f"Successfully fetched {len(repositories)} repository(ies) with name '{name}' in region '{region}'"
    else:
        # Get all repositories for this region
        repositories = crud.get_all_git_repositories(db, region)
        repository_dicts = [
            schemas.GitRepository.model_validate(repo.to_dict()).model_dump()
            for repo in repositories
        ]
        message = f"Successfully fetched all git repositories in region '{region}'"
    return StandardResponse(data=repository_dicts, message=message)


@china_router.post("/create", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@fujian_router.post("/create", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def create_git_repository_cn(repository: schemas.GitRepositoryCreate, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Create a new git repository record (region must be 'cn'). **This endpoint requires API token verification**
    
    :param repository: Git repository object to create
    :param db: Database session
    :return: StandardResponse object with created repository data
    """
    # Validate region is 'cn'
    if repository.region != "cn":
        raise HTTPException(status_code=400, detail=f"Region must be 'cn' for this endpoint, got '{repository.region}'")
    
    created_repository = crud.create_git_repository(db, repository)
    return StandardResponse(
        data=schemas.GitRepository.model_validate(created_repository.to_dict()).model_dump(),
        message="Git repository created successfully"
    )


@global_router.post("/create", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def create_git_repository_global(repository: schemas.GitRepositoryCreate, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Create a new git repository record (region must be 'global'). **This endpoint requires API token verification**
    
    :param repository: Git repository object to create
    :param db: Database session
    :return: StandardResponse object with created repository data
    """
    # Validate region is 'global'
    if repository.region != "global":
        raise HTTPException(status_code=400, detail=f"Region must be 'global' for this endpoint, got '{repository.region}'")
    
    created_repository = crud.create_git_repository(db, repository)
    return StandardResponse(
        data=schemas.GitRepository.model_validate(created_repository.to_dict()).model_dump(),
        message="Git repository created successfully"
    )


@china_router.put("/update", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@fujian_router.put("/update", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def update_git_repository_cn(
    repository: schemas.GitRepositoryUpdate,
    repo_id: int,
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Update a git repository by ID in the 'cn' region. **This endpoint requires API token verification**
    
    :param repository: Git repository update data
    :param repo_id: Repository ID (required)
    :param db: Database session
    :return: StandardResponse object with updated repository data
    """
    try:
        updated_repository = crud.update_git_repository(db, repo_id, repository)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not updated_repository:
        raise HTTPException(status_code=404, detail="Git repository not found")
    
    return StandardResponse(
        data=schemas.GitRepository.model_validate(updated_repository.to_dict()).model_dump(),
        message="Git repository updated successfully"
    )


@global_router.put("/update", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def update_git_repository_global(
    repository: schemas.GitRepositoryUpdate,
    repo_id: int,
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Update a git repository by ID in the 'global' region. **This endpoint requires API token verification**
    
    :param repository: Git repository update data
    :param repo_id: Repository ID (required)
    :param db: Database session
    :return: StandardResponse object with updated repository data
    """
    try:
        updated_repository = crud.update_git_repository(db, repo_id, repository)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not updated_repository:
        raise HTTPException(status_code=404, detail="Git repository not found")
    
    return StandardResponse(
        data=schemas.GitRepository.model_validate(updated_repository.to_dict()).model_dump(),
        message="Git repository updated successfully"
    )


@china_router.delete("/delete", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@fujian_router.delete("/delete", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def delete_git_repository_cn(
    repo_id: int,
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Delete a git repository by ID in the 'cn' region. **This endpoint requires API token verification**
    
    :param repo_id: Repository ID (required)
    :param db: Database session
    :return: StandardResponse object confirming deletion
    """
    success = crud.delete_git_repository(db, repo_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Git repository not found")
    
    return StandardResponse(
        data={"success": True},
        message="Git repository deleted successfully"
    )


@global_router.delete("/delete", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def delete_git_repository_global(
    repo_id: int,
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Delete a git repository by ID in the 'global' region. **This endpoint requires API token verification**
    
    :param repo_id: Repository ID (required)
    :param db: Database session
    :return: StandardResponse object confirming deletion
    """
    success = crud.delete_git_repository(db, repo_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Git repository not found")
    
    return StandardResponse(
        data={"success": True},
        message="Git repository deleted successfully"
    )
