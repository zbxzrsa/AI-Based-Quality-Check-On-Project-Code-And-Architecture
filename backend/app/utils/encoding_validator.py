"""
UTF-8 encoding validation utility for database migration files
"""
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path
import chardet

logger = logging.getLogger(__name__)


@dataclass
class EncodingValidationResult:
    """Result of encoding validation"""
    is_valid: bool
    detected_encoding: Optional[str]
    confidence: float
    errors: List[str]
    file_path: str
    
    def __str__(self) -> str:
        """String representation of validation result"""
        if self.is_valid:
            return f"Valid UTF-8 encoding for {self.file_path}"
        else:
            return f"Invalid encoding for {self.file_path}: {', '.join(self.errors)}"


@dataclass
class EncodingFixResult:
    """Result of encoding fix attempt"""
    success: bool
    original_encoding: Optional[str]
    fixed_content: Optional[str]
    errors: List[str]
    
    def __str__(self) -> str:
        """String representation of fix result"""
        if self.success:
            return f"Successfully fixed encoding from {self.original_encoding} to UTF-8"
        else:
            return f"Failed to fix encoding: {', '.join(self.errors)}"


class EncodingValidator:
    """Utility class for validating and fixing UTF-8 encoding in files"""
    
    def __init__(self):
        """Initialize encoding validator"""
        self.supported_encodings = ['utf-8', 'utf-8-sig', 'ascii']
        self.fallback_encodings = ['latin1', 'cp1252', 'iso-8859-1']
    
    def validate_file_encoding(self, file_path: Path) -> EncodingValidationResult:
        """
        Validate that a file is properly UTF-8 encoded
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            EncodingValidationResult with validation details
        """
        errors = []
        detected_encoding = None
        confidence = 0.0
        
        try:
            if not file_path.exists():
                errors.append(f"File does not exist: {file_path}")
                return EncodingValidationResult(
                    is_valid=False,
                    detected_encoding=None,
                    confidence=0.0,
                    errors=errors,
                    file_path=str(file_path)
                )
            
            # Read file as bytes for encoding detection
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            if not raw_data:
                # Empty file is valid UTF-8
                return EncodingValidationResult(
                    is_valid=True,
                    detected_encoding='utf-8',
                    confidence=1.0,
                    errors=[],
                    file_path=str(file_path)
                )
            
            # Detect encoding using chardet
            detection_result = chardet.detect(raw_data)
            detected_encoding = detection_result.get('encoding', '').lower() if detection_result.get('encoding') else None
            confidence = detection_result.get('confidence', 0.0)
            
            logger.debug(f"Detected encoding for {file_path}: {detected_encoding} (confidence: {confidence})")
            
            # Try to decode as UTF-8 first
            try:
                raw_data.decode('utf-8')
                # Successfully decoded as UTF-8
                return EncodingValidationResult(
                    is_valid=True,
                    detected_encoding='utf-8',
                    confidence=1.0,
                    errors=[],
                    file_path=str(file_path)
                )
            except UnicodeDecodeError as e:
                errors.append(f"UTF-8 decode error at byte {e.start}: {e.reason}")
                logger.warning(f"UTF-8 decode error in {file_path}: {e}")
            
            # Check if detected encoding is compatible
            if detected_encoding and detected_encoding in self.supported_encodings:
                # Try to read with detected encoding and convert to UTF-8
                try:
                    content = raw_data.decode(detected_encoding)
                    # If we can decode it, it's potentially fixable
                    if detected_encoding != 'utf-8':
                        errors.append(f"File is encoded as {detected_encoding}, not UTF-8")
                except UnicodeDecodeError as e:
                    errors.append(f"Cannot decode with detected encoding {detected_encoding}: {e}")
            else:
                if detected_encoding:
                    errors.append(f"Unsupported encoding detected: {detected_encoding}")
                else:
                    errors.append("Could not detect file encoding")
            
        except Exception as e:
            errors.append(f"Error validating file encoding: {e}")
            logger.error(f"Error validating encoding for {file_path}: {e}")
        
        is_valid = len(errors) == 0
        
        return EncodingValidationResult(
            is_valid=is_valid,
            detected_encoding=detected_encoding,
            confidence=confidence,
            errors=errors,
            file_path=str(file_path)
        )
    
    def validate_directory_encoding(self, directory_path: Path, pattern: str = "*.py") -> List[EncodingValidationResult]:
        """
        Validate encoding for all files matching pattern in directory
        
        Args:
            directory_path: Path to directory to scan
            pattern: File pattern to match (default: *.py)
            
        Returns:
            List of EncodingValidationResult for each file
        """
        results = []
        
        try:
            if not directory_path.exists():
                logger.warning(f"Directory does not exist: {directory_path}")
                return results
            
            for file_path in directory_path.glob(pattern):
                if file_path.is_file():
                    result = self.validate_file_encoding(file_path)
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"Error validating directory encoding: {e}")
            # Create error result for directory
            results.append(EncodingValidationResult(
                is_valid=False,
                detected_encoding=None,
                confidence=0.0,
                errors=[f"Error scanning directory: {e}"],
                file_path=str(directory_path)
            ))
        
        return results
    
    def fix_encoding_issues(self, file_path: Path) -> EncodingFixResult:
        """
        Attempt to fix encoding issues in a file
        
        Args:
            file_path: Path to the file to fix
            
        Returns:
            EncodingFixResult with fix details
        """
        errors = []
        original_encoding = None
        fixed_content = None
        
        try:
            if not file_path.exists():
                errors.append(f"File does not exist: {file_path}")
                return EncodingFixResult(
                    success=False,
                    original_encoding=None,
                    fixed_content=None,
                    errors=errors
                )
            
            # Read file as bytes
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            if not raw_data:
                # Empty file, nothing to fix
                return EncodingFixResult(
                    success=True,
                    original_encoding='utf-8',
                    fixed_content='',
                    errors=[]
                )
            
            # Detect current encoding
            detection_result = chardet.detect(raw_data)
            original_encoding = detection_result.get('encoding', '').lower() if detection_result.get('encoding') else None
            
            # Try to decode with detected encoding
            content = None
            for encoding in [original_encoding] + self.fallback_encodings:
                if not encoding:
                    continue
                try:
                    content = raw_data.decode(encoding)
                    original_encoding = encoding
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if content is None:
                errors.append("Could not decode file with any supported encoding")
                return EncodingFixResult(
                    success=False,
                    original_encoding=original_encoding,
                    fixed_content=None,
                    errors=errors
                )
            
            # Content successfully decoded, now it's UTF-8 compatible
            fixed_content = content
            
            logger.info(f"Successfully converted {file_path} from {original_encoding} to UTF-8")
            
        except Exception as e:
            errors.append(f"Error fixing encoding: {e}")
            logger.error(f"Error fixing encoding for {file_path}: {e}")
        
        success = len(errors) == 0 and fixed_content is not None
        
        return EncodingFixResult(
            success=success,
            original_encoding=original_encoding,
            fixed_content=fixed_content,
            errors=errors
        )
    
    def create_utf8_file(self, file_path: Path, content: str) -> bool:
        """
        Create a new file with proper UTF-8 encoding
        
        Args:
            file_path: Path where to create the file
            content: Content to write
            
        Returns:
            True if file was created successfully, False otherwise
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write with explicit UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            
            # Validate the created file
            validation_result = self.validate_file_encoding(file_path)
            if not validation_result.is_valid:
                logger.error(f"Created file {file_path} failed UTF-8 validation: {validation_result.errors}")
                return False
            
            logger.debug(f"Successfully created UTF-8 file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating UTF-8 file {file_path}: {e}")
            return False
    
    def get_problematic_lines(self, file_path: Path) -> List[Tuple[int, str, str]]:
        """
        Get lines that contain encoding problems
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            List of tuples (line_number, line_content, error_description)
        """
        problematic_lines = []
        
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            lines = raw_data.split(b'\n')
            
            for line_num, line_bytes in enumerate(lines, 1):
                try:
                    line_bytes.decode('utf-8')
                except UnicodeDecodeError as e:
                    # Try to get a readable representation of the line
                    try:
                        line_content = line_bytes.decode('utf-8', errors='replace')
                    except (UnicodeDecodeError, AttributeError) as e:
                        # Fallback for encoding issues
                        line_content = str(line_bytes)
                    
                    error_desc = f"UTF-8 decode error at position {e.start}: {e.reason}"
                    problematic_lines.append((line_num, line_content, error_desc))
                    
        except Exception as e:
            logger.error(f"Error analyzing problematic lines in {file_path}: {e}")
        
        return problematic_lines