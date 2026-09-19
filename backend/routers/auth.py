"""Registration, login, and "who am I".  OWNER: backend engineer."""
from fastapi import APIRouter, Depends, HTTPException

from ..database import connect
from ..deps import get_current_student
from ..schemas import LoginRequest, StudentRegister, TokenResponse
from ..services import auth as auth_service

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=TokenResponse)
def register(payload: StudentRegister):
    with connect() as db:
        existing = db.execute(
            'SELECT student_id FROM students WHERE student_id=?', (payload.student_id,)
        ).fetchone()
        if existing:
            # An account, not a profile -- re-registering the same id is a
            # conflict now, unlike the old idempotent-upsert /students/register.
            raise HTTPException(409, 'student_id already registered')
        db.execute(
            'INSERT INTO students(student_id,display_name,grade_level,password_hash) '
            'VALUES(?,?,?,?)',
            (
                payload.student_id,
                payload.display_name,
                payload.grade_level,
                auth_service.hash_password(payload.password),
            ),
        )
        db.commit()
    return TokenResponse(
        access_token=auth_service.create_token(payload.student_id),
        student_id=payload.student_id,
    )


@router.post('/login', response_model=TokenResponse)
def login(payload: LoginRequest):
    with connect() as db:
        row = db.execute(
            'SELECT password_hash FROM students WHERE student_id=?', (payload.student_id,)
        ).fetchone()
    if row is None or not row[0] or not auth_service.verify_password(payload.password, row[0]):
        raise HTTPException(401, 'Invalid student_id or password')
    return TokenResponse(
        access_token=auth_service.create_token(payload.student_id),
        student_id=payload.student_id,
    )


@router.get('/me')
def me(current_student: str = Depends(get_current_student)):
    with connect() as db:
        row = db.execute(
            'SELECT student_id,display_name,grade_level FROM students WHERE student_id=?',
            (current_student,),
        ).fetchone()
    if row is None:
        raise HTTPException(404, 'Student not found')
    return {'student_id': row[0], 'display_name': row[1], 'grade_level': row[2]}
