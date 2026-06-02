import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl


SERVICE_NAME = os.getenv("SERVICE_NAME", "ai-vision")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.4.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")

app = FastAPI(
    title="FIT4110 Lab 04 - AI Vision Service",
    version=SERVICE_VERSION,
    description="Dockerized AI Vision API aligned with the Lab 02 and Lab 03 contract.",
)


class DetectionPriority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class DetectionStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ObjectType(str, Enum):
    person = "person"
    vehicle = "vehicle"
    bag = "bag"
    unknown_object = "unknown_object"


class ProblemError(BaseModel):
    field: str
    code: str
    message: str


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: Optional[str] = None
    instance: Optional[str] = None
    errors: List[ProblemError] = Field(default_factory=list)


class HealthStatus(BaseModel):
    status: str
    service: str
    time: str


class CameraLocation(BaseModel):
    building: str = Field(..., min_length=1, max_length=20)
    floor: str = Field(..., min_length=1, max_length=10)
    zone: str = Field(..., min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")


class DetectionRequest(BaseModel):
    cameraId: str = Field(..., min_length=3, max_length=40, pattern=r"^CAM-[A-Z0-9]+-[0-9]{3}$")
    correlationId: str = Field(..., min_length=8, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")
    capturedAt: datetime
    imageUrl: HttpUrl
    motionScore: float = Field(..., ge=0, le=1)
    priority: DetectionPriority = DetectionPriority.normal
    location: Optional[CameraLocation] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BoundingBox(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)


class DetectedObject(BaseModel):
    objectType: ObjectType
    label: str
    confidence: float = Field(..., ge=0, le=1)
    bbox: BoundingBox
    trackingId: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class DetectionResult(BaseModel):
    detectionId: str
    correlationId: str
    status: DetectionStatus
    riskLevel: RiskLevel
    confidence: float = Field(..., ge=0, le=1)
    objects: List[DetectedObject]
    createdAt: str
    completedAt: Optional[str]
    message: Optional[str] = None


class VisionModelInfo(BaseModel):
    modelId: str
    modelName: str
    version: str
    status: str
    supportedObjectTypes: List[ObjectType]
    updatedAt: Optional[str]
    notes: Optional[str]


DETECTIONS: Dict[str, DetectionResult] = {}
CORRELATION_PAYLOADS: Dict[str, Dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    problem_type: str,
    errors: Optional[List[ProblemError]] = None,
) -> Dict[str, Any]:
    return Problem(
        type=problem_type,
        title=title,
        status=status_code,
        detail=detail,
        instance=instance,
        errors=errors or [],
    ).model_dump()


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing or invalid bearer token",
                instance="/vision/detect",
                problem_type="https://smart-campus.local/errors/unauthorized",
            ),
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    problem = exc.detail if isinstance(exc.detail, dict) else build_problem(
        status_code=exc.status_code,
        title=status.HTTP_STATUS_CODES.get(exc.status_code, "HTTP Error"),
        detail=str(exc.detail),
        instance=str(request.url.path),
        problem_type="about:blank",
    )
    problem["instance"] = problem.get("instance") or str(request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first_error.get("loc", []))
    message = first_error.get("msg", "Request validation error")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=f"{field}: {message}" if field else message,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/errors/validation",
            errors=[
                ProblemError(
                    field=field or "body",
                    code="VALIDATION_ERROR",
                    message=message,
                )
            ],
        ),
        media_type="application/problem+json",
    )


def detection_id_for(index: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"det-{today}-{index:04d}"


def risk_from_motion(motion_score: float) -> RiskLevel:
    if motion_score >= 0.95:
        return RiskLevel.critical
    if motion_score >= 0.75:
        return RiskLevel.high
    if motion_score >= 0.4:
        return RiskLevel.medium
    return RiskLevel.low


@app.get("/health", response_model=HealthStatus)
def get_health() -> HealthStatus:
    return HealthStatus(status="ok", service=SERVICE_NAME, time=now_iso())


@app.post("/vision/detect", response_model=DetectionResult, dependencies=[Depends(verify_bearer_token)])
def create_vision_detection(
    payload: DetectionRequest,
    x_model_state: Optional[str] = Header(default=None),
) -> DetectionResult:
    if x_model_state == "unavailable":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=build_problem(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                title="AI Vision unavailable",
                detail="Model is unavailable; consumer should retry with backoff",
                instance="/vision/detect",
                problem_type="https://smart-campus.local/errors/service-unavailable",
            ),
        )

    comparable_payload = payload.model_dump(mode="json")
    previous_payload = CORRELATION_PAYLOADS.get(payload.correlationId)

    if previous_payload is not None and previous_payload != comparable_payload:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_problem(
                status_code=status.HTTP_409_CONFLICT,
                title="Correlation ID conflict",
                detail="correlationId was already used with a different payload",
                instance="/vision/detect",
                problem_type="https://smart-campus.local/errors/conflict",
                errors=[
                    ProblemError(
                        field="correlationId",
                        code="IDEMPOTENCY_CONFLICT",
                        message="correlationId must not be reused for a different payload",
                    )
                ],
            ),
        )

    if previous_payload is not None:
        for result in DETECTIONS.values():
            if result.correlationId == payload.correlationId:
                return result

    created_at = now_iso()
    detection_id = detection_id_for(len(DETECTIONS) + 1)
    risk_level = risk_from_motion(payload.motionScore)
    confidence = min(0.99, max(0.0, round(payload.motionScore + 0.07, 2)))
    objects: List[DetectedObject] = []

    if payload.motionScore >= 0.4:
        objects.append(
            DetectedObject(
                objectType=ObjectType.person,
                label="person",
                confidence=confidence,
                bbox=BoundingBox(x=120, y=80, width=240, height=420),
                trackingId="track-001" if payload.motionScore >= 0.75 else None,
                attributes={"source": "mock-model"},
            )
        )

    result = DetectionResult(
        detectionId=detection_id,
        correlationId=payload.correlationId,
        status=DetectionStatus.completed,
        riskLevel=risk_level,
        confidence=confidence,
        objects=objects,
        createdAt=created_at,
        completedAt=created_at,
        message="AI Vision processed the camera frame",
    )
    CORRELATION_PAYLOADS[payload.correlationId] = comparable_payload
    DETECTIONS[detection_id] = result
    return result


@app.get("/vision/detections/{detection_id}", response_model=DetectionResult, dependencies=[Depends(verify_bearer_token)])
def get_vision_detection_by_id(detection_id: str) -> DetectionResult:
    result = DETECTIONS.get(detection_id)
    if result is None and detection_id == "det-20260519-0001":
        result = DetectionResult(
            detectionId=detection_id,
            correlationId="corr-20260519-0001",
            status=DetectionStatus.completed,
            riskLevel=RiskLevel.high,
            confidence=0.94,
            objects=[
                DetectedObject(
                    objectType=ObjectType.person,
                    label="person",
                    confidence=0.92,
                    bbox=BoundingBox(x=120, y=80, width=240, height=420),
                    trackingId="track-001",
                    attributes={"source": "seed"},
                )
            ],
            createdAt="2026-05-19T03:30:01Z",
            completedAt="2026-05-19T03:30:02Z",
            message="Seed detection for contract polling test",
        )
        DETECTIONS[detection_id] = result

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=build_problem(
                status_code=status.HTTP_404_NOT_FOUND,
                title="Detection not found",
                detail="detectionId does not exist",
                instance=f"/vision/detections/{detection_id}",
                problem_type="https://smart-campus.local/errors/not-found",
            ),
        )

    return result


@app.get("/vision/models/info", response_model=VisionModelInfo, dependencies=[Depends(verify_bearer_token)])
def get_vision_model_info() -> VisionModelInfo:
    return VisionModelInfo(
        modelId="vision-b4-mock-campus-v1",
        modelName="Campus Mock Vision Detector",
        version=SERVICE_VERSION,
        status="ready",
        supportedObjectTypes=[
            ObjectType.person,
            ObjectType.vehicle,
            ObjectType.bag,
            ObjectType.unknown_object,
        ],
        updatedAt="2026-06-02T00:00:00Z",
        notes="Lightweight mock model packaged for FIT4110 Lab 04 Docker verification",
    )
