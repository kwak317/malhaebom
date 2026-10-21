from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from app.services.resume_assistance import ResumeAssistanceService, PolishRequest, AssistanceUnavailable
from app.services.resume_analysis import MAX_PDF_BYTES

def register_resume_assistance_routes(app, require_authenticated_user):
    service=ResumeAssistanceService()
    def error_response(error):
        return JSONResponse(status_code=422 if isinstance(error,ValueError) else 503,content={'detail':str(error)},headers={'Cache-Control':'no-store'})
    @app.post('/api/resume/assist/import')
    async def import_resume(file: UploadFile=File(...),consent: bool=Form(...),user=Depends(require_authenticated_user)):
        if not consent: raise HTTPException(status_code=403,detail='동의 후 정보 가져오기를 진행해 주세요.')
        try:
            data=await file.read(MAX_PDF_BYTES+1)
            # The entire file is request-scoped; it is never sent to storage.
            from starlette.concurrency import run_in_threadpool
            output=await run_in_threadpool(service.import_pdf,data)
            return JSONResponse(content=output,headers={'Cache-Control':'no-store'})
        except (ValueError,AssistanceUnavailable) as error: return error_response(error)
        finally: await file.close()
    @app.post('/api/resume/assist/polish')
    def polish_resume(request: PolishRequest,user=Depends(require_authenticated_user)):
        try: return JSONResponse(content=service.polish(request),headers={'Cache-Control':'no-store'})
        except (ValueError,AssistanceUnavailable) as error: return error_response(error)
