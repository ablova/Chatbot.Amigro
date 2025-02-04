# Ubicación /home/pablollh/app/utilidades/parser.py

import unicodedata
import imaplib
import email
import asyncio
from app.models import ConfiguracionBU, Person
from functools import lru_cache
from pathlib import Path
import spacy
from app.models import Person, ConfiguracionBU, Division, Skill
from typing import List, Dict, Tuple, Optional
from django.utils.timezone import now
from datetime import datetime
from app.chatbot.nlp import sn  # SkillNer instance
from app.chatbot.integrations.services import send_message, send_email
import logging

logger = logging.getLogger(__name__)

# Diccionario de folders por acción
FOLDER_CONFIG = {
    "cv_folder": "INBOX/CV",  # Reemplaza por la ruta correcta
    "parsed_folder": "INBOX/Parsed",
    "error_folder": "INBOX/Error",
}

@lru_cache(maxsize=1)
def load_spacy_model():
    return spacy.load("es_core_news_sm")

def normalize_text(text):
    """
    Normaliza el texto eliminando acentos y convirtiendo a minúsculas.
    """
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    return text.lower()

class CVParser:
    def __init__(self, business_unit):
        """
        Initializes the CVParser for a specific business unit.
        """
        self.business_unit = business_unit
        self.nlp = load_spacy_model()
        self.analysis_points = self.get_analysis_points()
        self.cross_analysis = self.get_cross_analysis()

    def get_analysis_points(self):
        """
        Returns the primary analysis points based on the business unit.
        """
        analysis_points = {
            'huntRED®': ['leadership_skills', 'executive_experience', 'achievements', 'management_experience', 'responsibilities', 'language_skills'],
            'huntRED® Executive': ['strategic_planning', 'board_experience', 'global_exposure', 'executive_experience', 'responsibilities', 'language_skills', 'international_experience'],
            'huntu': ['education', 'projects', 'skills', 'potential_for_growth', 'achievements'],
            'amigro': ['work_authorization', 'language_skills', 'international_experience', 'skills'],
        }
        default_analysis = ['skills', 'experience', 'education']
        return analysis_points.get(self.business_unit.name, default_analysis)

    def get_cross_analysis(self):
        """
        Returns analysis points for cross-checking between units to ensure flexibility.
        """
        cross_analysis = {
            'huntRED®': ['strategic_planning', 'board_experience'],  # Consider huntRED Executive attributes
            'huntRED® Executive': ['management_experience', 'achievements'],  # Consider huntRED attributes
            'huntu': ['achievements', 'management_experience'],  # Check readiness for huntRED
            'amigro': []  # No cross-analysis for Amigro, as the boundary is clear
        }
        return cross_analysis.get(self.business_unit.name, [])

    def parse(self, cv_text):
        """
        Parses the CV text to extract relevant information based on the business unit and cross-analysis.
        """
        doc = self.nlp(cv_text)
        results = {}

        # Primary analysis
        for point in self.analysis_points:
            results[point] = self.extract_information(doc, point)

        # Cross-analysis
        if self.cross_analysis:
            results['cross_analysis'] = {}
            for point in self.cross_analysis:
                results['cross_analysis'][point] = self.extract_information(doc, point)

        return results

    def extract_information(self, doc, point):
        """
        Extrae información específica basada en un punto de análisis.
        """
        if point == "skills":
            return self.extract_skills(doc)
        elif point == "experience":
            return self.extract_experience(doc)
        elif point == "education":
            return self.extract_education(doc)
        elif point == "achievements":
            return self.extract_achievements(doc)
        elif point == "management_experience":
            return self.extract_management_experience(doc)
        elif point == "leadership_skills":
            return self.extract_leadership_skills(doc)
        elif point == "language_skills":
            return self.extract_language_skills(doc)
        elif point == "work_authorization":
            return self.extract_work_authorization(doc)
        elif point == "strategic_planning":
            return self.extract_strategic_planning(doc)
        elif point == "board_experience":
            return self.extract_board_experience(doc)
        elif point == "global_exposure":
            return self.extract_global_exposure(doc)
        elif point == "international_experience":
            return self.extract_international_experience(doc)
        else:
            return f"Analysis point '{point}' is not defined."

    # Métodos específicos mejorados
    def extract_skills(self, doc):
        """
        Extrae habilidades del texto utilizando SkillNer.
        """
        skills = sn.extract_skills(doc.text)
        extracted_skills = [skill['skill'] for skill in skills]
        logger.debug(f"Habilidades extraídas: {extracted_skills}")
        return extracted_skills

    def extract_experience(self, doc):
        """
        Extrae experiencia laboral en formato estructurado.
        """
        experiences = []
        experience_keywords = ["trabajé", "trabajo", "puesto", "empleo", "cargo", "experiencia", "desempeñé"]
        for sent in doc.sents:
            if any(keyword in sent.text.lower() for keyword in experience_keywords):
                experiences.append(sent.text.strip())
        logger.debug(f"Experiencias extraídas: {experiences}")
        return experiences

    def extract_education(self, doc):
        """
        Extrae información educativa en formato estructurado.
        """
        education = []
        education_keywords = ["licenciatura", "maestría", "doctorado", "carrera", "universidad", "instituto"]
        for sent in doc.sents:
            if any(keyword in sent.text.lower() for keyword in education_keywords):
                education.append(sent.text.strip())
        logger.debug(f"Educación extraída: {education}")
        return education

    def extract_achievements(self, doc):
        """
        Extrae logros destacados.
        """
        achievements = []
        achievement_keywords = ["logré", "alcancé", "implementé", "desarrollé", "aumenté", "reduje", "optimizé"]
        for sent in doc.sents:
            if any(keyword in sent.text.lower() for keyword in achievement_keywords):
                achievements.append(sent.text.strip())
        logger.debug(f"Logros extraídos: {achievements}")
        return achievements

    def extract_management_experience(self, doc):
        """
        Extrae experiencia en gestión.
        """
        management_experience = []
        management_keywords = ["lideré", "supervisé", "coordinar", "dirigir", "gerente", "manager"]
        for sent in doc.sents:
            if any(keyword in sent.text.lower() for keyword in management_keywords):
                management_experience.append(sent.text.strip())
        logger.debug(f"Experiencia de gestión extraída: {management_experience}")
        return management_experience

    def extract_leadership_skills(self, doc):
        """
        Extrae habilidades de liderazgo.
        """
        leadership_skills = []
        leadership_keywords = ["liderazgo", "trabajo en equipo", "comunicación", "motivación", "influencia"]
        for token in doc:
            if token.text.lower() in leadership_keywords:
                leadership_skills.append(token.text)
        logger.debug(f"Habilidades de liderazgo extraídas: {leadership_skills}")
        return leadership_skills

    def extract_language_skills(self, doc):
        """
        Extrae habilidades lingüísticas.
        """
        languages = []
        language_keywords = ["español", "inglés", "francés", "alemán", "portugués", "bilingüe"]
        for token in doc:
            if token.text.lower() in language_keywords:
                languages.append(token.text)
        logger.debug(f"Habilidades lingüísticas extraídas: {languages}")
        return languages

    def extract_work_authorization(self, doc):
        """
        Extrae información sobre autorización de trabajo.
        """
        work_authorization = []
        work_keywords = ["permiso de trabajo", "visa", "estatus migratorio", "autorización laboral"]
        for sent in doc.sents:
            if any(keyword in sent.text.lower() for keyword in work_keywords):
                work_authorization.append(sent.text.strip())
        logger.debug(f"Autorización de trabajo extraída: {work_authorization}")
        return work_authorization

    # Métodos adicionales para análisis específicos
    def extract_strategic_planning(self, doc):
        """
        Extrae información relacionada con planificación estratégica.
        """
        strategic_planning = []
        keywords = ["planificación estratégica", "estrategia empresarial", "desarrollo estratégico"]
        for sent in doc.sents:
            if any(keyword in sent.text.lower() for keyword in keywords):
                strategic_planning.append(sent.text.strip())
        logger.debug(f"Planificación estratégica extraída: {strategic_planning}")
        return strategic_planning

    def extract_board_experience(self, doc):
        """
        Extrae experiencia en consejos de administración.
        """
        board_experience = []
        keywords = ["consejo de administración", "miembro del consejo", "board member"]
        for sent in doc.sents:
            if any(keyword in sent.text.lower() for keyword in keywords):
                board_experience.append(sent.text.strip())
        logger.debug(f"Experiencia en consejo de administración extraída: {board_experience}")
        return board_experience

    def extract_global_exposure(self, doc):
        """
        Extrae información sobre exposición global.
        """
        global_exposure = []
        keywords = ["exposición global", "trabajo internacional", "proyectos en el extranjero"]
        for sent in doc.sents:
            if any(keyword in sent.text.lower() for keyword in keywords):
                global_exposure.append(sent.text.strip())
        logger.debug(f"Exposición global extraída: {global_exposure}")
        return global_exposure

    def extract_international_experience(self, doc):
        """
        Extrae experiencia internacional.
        """
        international_experience = []
        keywords = ["experiencia internacional", "trabajo en el extranjero", "proyectos internacionales"]
        for sent in doc.sents:
            if any(keyword in sent.text.lower() for keyword in keywords):
                international_experience.append(sent.text.strip())
        logger.debug(f"Experiencia internacional extraída: {international_experience}")
        return international_experience

    def associate_divisions(skills: List[str]) -> List[str]:
        associated_divisions = set()
        skills_lower = set(skill.lower() for skill in skills)
        for division, division_skills in DIVISION_SKILLS.items():
            if skills_lower.intersection(set(skill.lower() for skill in division_skills)):
                associated_divisions.add(division)
        return list(associated_divisions)

    def parse_and_match_candidate(self, file_path):
        """
        Procesa un CV y busca coincidencias de candidatos existentes.
        """
        parsed_data = self._extract_text(file_path)
        if not parsed_data:
            logger.warning(f"No se pudo extraer datos del CV: {file_path}")
            return

        email = parsed_data.get("email")
        phone = parsed_data.get("phone")

        # Buscar candidato existente
        candidate = Person.objects.filter(email=email).first() or Person.objects.filter(phone=phone).first()

        if candidate:
            self._update_candidate(candidate, parsed_data, file_path)
        else:
            self._create_new_candidate(parsed_data, file_path)

    def _extract_text(self, file_path):
        """
        Extrae texto desde archivos de CV (PDF o Word).
        """
        try:
            if file_path.suffix.lower() == '.pdf':
                text = extract_text_pdf(str(file_path))
            elif file_path.suffix.lower() in ['.doc', '.docx']:
                doc = docx.Document(str(file_path))
                text = "\n".join([para.text for para in doc.paragraphs])
            else:
                logger.warning(f"Formato de archivo no soportado: {file_path}")
                return {}
            
            # Procesamiento básico del texto para extraer información relevante
            parsed_data = self.parse(text)
            return parsed_data
        except Exception as e:
            logger.error(f"Error extrayendo texto de {file_path}: {e}")
            return {}

    def _update_candidate(self, candidate, parsed_data, file_path):
        """
        Actualiza información del candidato existente.
        """
        candidate.cv_file = file_path
        candidate.cv_analysis = parsed_data
        candidate.cv_parsed = True
        candidate.metadata["last_cv_update"] = now().isoformat()

        # Extraer y asociar habilidades y divisiones
        skills = self.extract_skills(parsed_data.get("skills", ""))
        divisions = self.associate_divisions(skills)
        candidate.metadata["skills"] = list(set(candidate.metadata.get("skills", []) + skills))
        candidate.metadata["divisions"] = list(set(candidate.metadata.get("divisions", []) + divisions))

        candidate.save()
        logger.info(f"Perfil actualizado: {candidate.nombre} {candidate.apellido_paterno}")

    def _create_new_candidate(self, parsed_data, file_path):
        """
        Crea un nuevo candidato si no existe.
        """
        skills = self.extract_skills(parsed_data.get("skills", ""))
        divisions = self.associate_divisions(skills)

        candidate = Person.objects.create(
            nombre=parsed_data.get("nombre"),
            apellido_paterno=parsed_data.get("apellido_paterno"),
            apellido_materno=parsed_data.get("apellido_materno"),
            email=parsed_data.get("email"),
            phone=parsed_data.get("phone"),
            skills=parsed_data.get("skills"),
            cv_file=file_path,
            cv_parsed=True,
            cv_analysis=parsed_data,
            metadata={
                "last_cv_update": now().isoformat(),
                "skills": skills,
                "divisions": divisions,
                "created_at": now().isoformat(),  # Se agrega fecha de creación en metadata
            }
        )
        logger.info(f"Nuevo perfil creado: {candidate.nombre} {candidate.apellido_paterno}")

# Diccionario de folders por acción
FOLDER_CONFIG = {
    "cv_folder": "CV",
    "parsed_folder": "Parsed",
    "error_folder": "Error",
}

class IMAPCVProcessor:
    def __init__(self, business_unit):
        """
        Inicializa el procesador con la configuración dinámica de la unidad de negocio.
        """
        self.business_unit = business_unit
        self.config = self._load_config(business_unit)
        self.parser = CVParser(business_unit)

    def _load_config(self, business_unit):
        """
        Carga la configuración de IMAP desde ConfiguracionBU.
        """
        try:
            config = ConfiguracionBU.objects.get(business_unit=business_unit)
            return {
                'server': config.smtp_host,
                'port': config.smtp_port,
                'username': config.smtp_username,
                'password': config.smtp_password,
                'use_tls': config.smtp_use_tls,
                'folders': FOLDER_CONFIG
            }
        except ConfiguracionBU.DoesNotExist:
            raise ValueError(f"No configuration found for business unit: {business_unit}")

    def _connect_imap(self):
        """
        Conecta al servidor IMAP usando la configuración proporcionada.
        """
        try:
            mail = imaplib.IMAP4_SSL(self.config['server'])
            mail.login(self.config['username'], self.config['password'])
            status, data = mail.select(self.config['folders']['cv_folder'])
            if status != "OK":
                raise Exception(f"Error al seleccionar el buzón: {data}")
            return mail
        except Exception as e:
            logger.error(f"Error conectando al servidor IMAP: {e}")
            return None

    def _move_email(self, mail, email_id, folder):
        """
        Mueve un correo a un folder específico.
        """
        try:
            mail.store(email_id, "+FLAGS", "\\Deleted")
            mail.copy(email_id, folder)
            mail.expunge()
            logger.info(f"Correo {email_id} movido a {folder}")
        except Exception as e:
            logger.error(f"Error moviendo correo {email_id} a {folder}: {e}")



    def _generate_summary_and_send_report(self, candidates_processed, candidates_created, candidates_updated):
        """
        Genera y envía un resumen del procesamiento al administrador.
        """
        admin_email = self.business_unit.configuracionbu.correo_bu
        if not admin_email:
            logger.warning("Correo del administrador no configurado. Resumen no enviado.")
            return

        summary = f"""
        <h2>Resumen del Procesamiento de CVs para {self.business_unit.name}:</h2>
        <ul>
            <li>Total de candidatos procesados: {candidates_processed}</li>
            <li>Nuevos candidatos creados: {candidates_created}</li>
            <li>Candidatos actualizados: {candidates_updated}</li>
        </ul>
        """

        logger.info(f"Resumen generado:\n{summary}")

        try:
            # Ejecutar `send_email` usando asyncio.run
            result = asyncio.run(send_email(
                business_unit_name=self.business_unit.name,
                subject=f"Resumen de Procesamiento de CVs - {self.business_unit.name}",
                to_email=admin_email,
                body=summary,
                from_email="noreply@huntred.com",
            ))

            if result.get("status") == "success":
                logger.info(f"Resumen enviado correctamente a {admin_email}.")
            else:
                logger.error(f"Error en el envío del correo: {result.get('message')}")

        except Exception as e:
            logger.error(f"Error enviando el resumen: {e}", exc_info=True)


    def process_emails(self):
        """
        Procesa los correos y genera un reporte al final.
        """
        mail = self._connect_imap()
        if not mail:
            return

        candidates_processed = 0
        candidates_created = 0
        candidates_updated = 0

        try:
            status, messages = mail.search(None, "ALL")
            email_ids = messages[0].split()

            for email_id in email_ids:
                try:
                    status, data = mail.fetch(email_id, "(RFC822)")
                    message = email.message_from_bytes(data[0][1])

                    attachments = self.parser.extract_attachments(message)
                    if not attachments:
                        logger.warning(f"Correo {email_id} sin adjuntos válidos. Moviendo a {FOLDER_CONFIG['error_folder']}.")
                        self._move_email(mail, email_id, FOLDER_CONFIG['error_folder'])
                        continue

                    for attachment in attachments:
                        result = self.parser.parse_and_match_candidate(attachment)
                        if result.get("status") == "created":
                            candidates_created += 1
                        elif result.get("status") == "updated":
                            candidates_updated += 1
                        candidates_processed += 1

                    self._move_email(mail, email_id, FOLDER_CONFIG['parsed_folder'])

                except Exception as e:
                    logger.error(f"Error procesando correo {email_id}: {e}")
                    self._move_email(mail, email_id, FOLDER_CONFIG['error_folder'])

        except Exception as e:
            logger.error(f"Error general procesando correos: {e}")

        finally:
            mail.logout()

        # Generar y enviar el resumen
        self._generate_summary_and_send_report(
            candidates_processed,
            candidates_created,
            candidates_updated
        )
