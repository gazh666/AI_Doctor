from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import ImageAnalysis
from app.core.deps import CurrentUser
from app.schemas.vision import (
    ImageUploadResponse,
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    XRayAnalysisRequest,
    XRayAnalysisResponse
)
from typing import Optional

router = APIRouter()
UNAUTHORIZED_RESPONSE = {
    401: {
        "description": "Not authenticated. Provide a valid Bearer access token.",
    }
}

@router.post("/analyze", response_model=ImageAnalysisResponse, responses=UNAUTHORIZED_RESPONSE)
async def analyze_medical_image(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    image_type: str = Form(...),
    patient_context: Optional[str] = Form(None),
    enhance_image: bool = Form(True),
    patient_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    from app.services.vision.gemini_vision import gemini_vision
    from app.services.vision.image_processor import image_processor

    try:
       
        image_data = await file.read()
        
        
        is_valid, error_msg = image_processor.validate_image(image_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
       
        metadata = image_processor.get_image_metadata(image_data)
        
        
        if enhance_image:
            image_data = image_processor.preprocess_image(image_data, enhance=True)
        
        
        analysis_result = await gemini_vision.analyze_medical_image(
            image_data=image_data,
            image_type=image_type,
            filename=file.filename,
            additional_context=patient_context
        )
        
       
        image_analysis = ImageAnalysis(
            user_id=current_user.id,
            patient_id=patient_id, 
            image_type=image_type,
            original_filename=file.filename,
            analysis_result=analysis_result,
            findings=analysis_result.get("findings_summary", "Review full report."),
            confidence=analysis_result.get("confidence", 0.8),
            severity=analysis_result.get("severity", "unknown"),
            recommendations=analysis_result.get("recommendations", "Consult with a physician.")
        )
        db.add(image_analysis)
        await db.commit()
        await db.refresh(image_analysis)
        
        return ImageAnalysisResponse(
            analysis_id=image_analysis.id,
            image_type=image_analysis.image_type,
            findings=image_analysis.findings,
            full_analysis=analysis_result.get("full_analysis", ""),
            severity=image_analysis.severity,
            confidence=image_analysis.confidence,
            recommendations=image_analysis.recommendations,
            metadata=metadata,
            created_at=image_analysis.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/xray/analyze", response_model=XRayAnalysisResponse, responses=UNAUTHORIZED_RESPONSE)
async def analyze_chest_xray(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    patient_id: Optional[int] = Form(None), 
    symptoms: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    gender: Optional[str] = Form(None),
    medical_history: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Specialized endpoint for chest X-ray analysis
    """
    from app.services.vision.gemini_vision import gemini_vision
    from app.services.vision.image_processor import image_processor

    try:
        # Read image
        image_data = await file.read()
        
        # Validate
        is_valid, error_msg = image_processor.validate_image(image_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Enhance image
        image_data = image_processor.preprocess_image(image_data, enhance=True)
        
        # Build context
        context_parts = []
        if age:
            context_parts.append(f"Patient age: {age}")
        if gender:
            context_parts.append(f"Gender: {gender}")
        if symptoms:
            context_parts.append(f"Symptoms: {symptoms}")
        if medical_history:
            context_parts.append(f"Medical history: {medical_history}")
        
        context = "\n".join(context_parts) if context_parts else None
        
        # Analyze
        analysis_result = await gemini_vision.analyze_medical_image(
            image_data=image_data,
            image_type="chest_xray",
            filename=file.filename,
            additional_context=context     
        )
        
        # Store in database
        image_analysis = ImageAnalysis(
            user_id=current_user.id,
            patient_id=patient_id, 
            image_type="chest_xray",
            original_filename=file.filename,
            analysis_result=analysis_result,
            findings=analysis_result.get("findings_summary", "See report."),
            confidence=analysis_result.get("confidence", 0.0),
            severity=analysis_result.get("severity", "unknown"),
            recommendations=analysis_result.get("recommendations", "")
        )
        
        db.add(image_analysis)
        await db.commit()
        
   
        full_text = analysis_result.get("full_analysis", "")
        
      
        findings = []
        for line in full_text.split('\n'):
            line = line.strip()
            
           
            if any(line.startswith(s) for s in ('-', '•', '*', '**')) and len(line) > 10:

                clean_line = line.replace('**', '').lstrip('-•* ').strip()
                
               
                is_header = clean_line.endswith(':') or clean_line.isupper()
                is_title = any(word in clean_line.upper() for word in ["ANALYSIS", "IMPRESSION", "ASSESSMENT", "LOCATIONS"])
                if not is_header and not is_title:
                    findings.append(clean_line)

        # Fallback
        if not findings and full_text:
            findings = ["Review the detailed analysis for specific observations."]
        
        
        differential = []
        found_section = False
        
        for line in full_text.split('\n'):
            line_lower = line.lower()
            
            if "differential diagnosis" in line_lower or "suggestive of" in line_lower:
                found_section = True
                continue
            
            
            if found_section:
                if line.strip().startswith(('-', '•', '*')):
                    diag = line.replace('**', '').lstrip('-•* ').strip()
                    if len(diag) > 3:
                        differential.append(diag)
                
                elif line.strip() == "" or (line.strip().startswith('**') and ":" in line):
                    if len(differential) > 0:
                        break

        
        if not differential:
            keywords = ["interstitial lung disease", "pneumonia", "edema", "effusion"]
            differential = [k.title() for k in keywords if k in full_text.lower()]
        
        
        urgent_flags = []
        severity_value = analysis_result.get("severity", "unknown").lower()
        
      
        if severity_value in ["severe", "critical", "urgent"]:
            urgent_flags.append(f"Urgent medical attention recommended: {severity_value.title()} case detected.")
        
       
        emergency_keywords = ["pneumothorax", "hemorrhage", "acute", "immediate intervention"]
        if any(key in " ".join(findings).lower() for key in emergency_keywords):
            if "No evidence of pneumothorax" not in " ".join(findings): # Avoid "no evidence" triggers
                urgent_flags.append("Clinical markers indicate potential acute condition.")
        
        return XRayAnalysisResponse(
            analysis_id=image_analysis.id,
            analysis=full_text,
            findings=findings[:5],
            severity=analysis_result.get("severity", "unknown"),
            confidence=analysis_result.get("confidence", 0.0),
            differential_diagnosis=differential,
            recommendations=analysis_result.get("recommendations", ""),
            urgent_flags=urgent_flags
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"X-ray analysis failed: {str(e)}")


@router.get("/analysis/{analysis_id}", response_model=ImageAnalysisResponse, responses=UNAUTHORIZED_RESPONSE)
async def get_analysis(
    analysis_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve previous image analysis"""
    
    result = await db.execute(
        select(ImageAnalysis).filter(
            ImageAnalysis.id == analysis_id,
            ImageAnalysis.user_id == current_user.id,
        )
    )
    analysis = result.scalars().first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return ImageAnalysisResponse(
        analysis_id=analysis.id,
        image_type=analysis.image_type,
        findings=analysis.findings,
        full_analysis=analysis.analysis_result.get("full_analysis", ""),
        severity=analysis.severity,
        confidence=analysis.confidence,
        recommendations=analysis.recommendations,
        metadata=analysis.analysis_result,
        created_at=analysis.created_at
    )


@router.get("/history", responses=UNAUTHORIZED_RESPONSE)
async def get_analysis_history(
    current_user: CurrentUser,
    limit: int = 10,
    image_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    
    query = select(ImageAnalysis).filter(ImageAnalysis.user_id == current_user.id)
    
    if image_type:
        query = query.filter(ImageAnalysis.image_type == image_type)
    
    result = await db.execute(query.order_by(ImageAnalysis.created_at.desc()).limit(limit))
    analyses = result.scalars().all()
    
    return {
        "total": len(analyses),
        "analyses": [
            {
                "id": a.id,
                "image_type": a.image_type,
                "filename": a.original_filename,
                "severity": a.severity,
                "confidence": a.confidence,
                "created_at": a.created_at
            }
            for a in analyses
        ]
    }
