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
    Get all git repositories from database (filtered by region=cn), or a specific repository by name if provided.
    **This endpoint requires API token verification**
    
    :param name: Optional repository name to filter by
    :param db: Database session
    :return: A list of git repository objects (or single repository if name is provided)
    """
    region = "cn"
    if name:
        # Get specific repository by name and region
        repository = crud.get_git_repository_by_name(db, name, region)
        if not repository:
            raise HTTPException(status_code=404, detail=f"Repository with name '{name}' and region '{region}' not found")
        repository_dicts = [schemas.GitRepository.model_validate(repository.to_dict()).model_dump()]
        message = f"Successfully fetched repository '{name}' in region '{region}'"
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
    Get all git repositories from database (filtered by region=global), or a specific repository by name if provided.
    **This endpoint requires API token verification**
    
    :param name: Optional repository name to filter by
    :param db: Database session
    :return: A list of git repository objects (or single repository if name is provided)
    """
    region = "global"
    if name:
        # Get specific repository by name and region
        repository = crud.get_git_repository_by_name(db, name, region)
        if not repository:
            raise HTTPException(status_code=404, detail=f"Repository with name '{name}' and region '{region}' not found")
        repository_dicts = [schemas.GitRepository.model_validate(repository.to_dict()).model_dump()]
        message = f"Successfully fetched repository '{name}' in region '{region}'"
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
    
    # Check if repository with the same name and region already exists
    existing = crud.get_git_repository_by_name(db, repository.name, repository.region)
    if existing:
        raise HTTPException(status_code=400, detail=f"Repository with name '{repository.name}' and region '{repository.region}' already exists")
    
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
    
    # Check if repository with the same name and region already exists
    existing = crud.get_git_repository_by_name(db, repository.name, repository.region)
    if existing:
        raise HTTPException(status_code=400, detail=f"Repository with name '{repository.name}' and region '{repository.region}' already exists")
    
    created_repository = crud.create_git_repository(db, repository)
    return StandardResponse(
        data=schemas.GitRepository.model_validate(created_repository.to_dict()).model_dump(),
        message="Git repository created successfully"
    )


@china_router.put("/update", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@fujian_router.put("/update", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def update_git_repository_cn(
    repository: schemas.GitRepositoryUpdate,
    repo_id: Optional[int] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Update a git repository by ID or name in the 'cn' region. **This endpoint requires API token verification**
    
    :param repository: Git repository update data
    :param repo_id: Repository ID (optional)
    :param name: Repository name (optional, will update the repository with this name in 'cn' region)
    :param db: Database session
    :return: StandardResponse object with updated repository data
    """
    if not repo_id and not name:
        raise HTTPException(status_code=400, detail="Either repo_id or name must be provided")
    
    try:
        if repo_id:
            updated_repository = crud.update_git_repository(db, repo_id, repository)
        else:
            # For name-based update, we need to specify region='cn'
            updated_repository = crud.update_git_repository_by_name(db, name, "cn", repository)
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
    repo_id: Optional[int] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Update a git repository by ID or name in the 'global' region. **This endpoint requires API token verification**
    
    :param repository: Git repository update data
    :param repo_id: Repository ID (optional)
    :param name: Repository name (optional, will update the repository with this name in 'global' region)
    :param db: Database session
    :return: StandardResponse object with updated repository data
    """
    if not repo_id and not name:
        raise HTTPException(status_code=400, detail="Either repo_id or name must be provided")
    
    try:
        if repo_id:
            updated_repository = crud.update_git_repository(db, repo_id, repository)
        else:
            # For name-based update, we need to specify region='global'
            updated_repository = crud.update_git_repository_by_name(db, name, "global", repository)
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
    repo_id: Optional[int] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Delete a git repository by ID or name in the 'cn' region. **This endpoint requires API token verification**
    
    :param repo_id: Repository ID (optional)
    :param name: Repository name (optional, will delete the repository with this name in 'cn' region)
    :param db: Database session
    :return: StandardResponse object confirming deletion
    """
    if not repo_id and not name:
        raise HTTPException(status_code=400, detail="Either repo_id or name must be provided")
    
    if repo_id:
        success = crud.delete_git_repository(db, repo_id)
    else:
        # For name-based delete, we need to specify region='cn'
        success = crud.delete_git_repository_by_name(db, name, "cn")
    
    if not success:
        raise HTTPException(status_code=404, detail="Git repository not found")
    
    return StandardResponse(
        data={"success": True},
        message="Git repository deleted successfully"
    )


@global_router.delete("/delete", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def delete_git_repository_global(
    repo_id: Optional[int] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Delete a git repository by ID or name in the 'global' region. **This endpoint requires API token verification**
    
    :param repo_id: Repository ID (optional)
    :param name: Repository name (optional, will delete the repository with this name in 'global' region)
    :param db: Database session
    :return: StandardResponse object confirming deletion
    """
    if not repo_id and not name:
        raise HTTPException(status_code=400, detail="Either repo_id or name must be provided")
    
    if repo_id:
        success = crud.delete_git_repository(db, repo_id)
    else:
        # For name-based delete, we need to specify region='global'
        success = crud.delete_git_repository_by_name(db, name, "global")
    
    if not success:
        raise HTTPException(status_code=404, detail="Git repository not found")
    
    return StandardResponse(
        data={"success": True},
        message="Git repository deleted successfully"
    )
