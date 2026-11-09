from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from pathlib import Path

def generate_pdf():
    output_path = Path(__file__).resolve().parent.parent / "modern_software_architecture.pdf"
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=10,
    )
    
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=10,
        spaceAfter=4,
    )

    h3_style = ParagraphStyle(
        'DocH3',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#334155'),
        spaceBefore=6,
        spaceAfter=2,
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6,
    )

    story = []

    story.append(Paragraph("Modern Software Architecture: Monolith to Microservices and Event-Driven Systems", title_style))
    story.append(Paragraph("<b>Technical Architecture Blueprint & Evaluation Guide</b>", body_style))
    story.append(Spacer(1, 6))

    # Section 1
    story.append(Paragraph("1. Introduction", h2_style))
    story.append(Paragraph(
        "Software architecture design is fundamentally driven by organizational scale, business agility, and domain complexity. "
        "Historically, organizations start with unified Monolithic Architectures. As domain boundaries grow, systems transition toward Microservices Architectures "
        "and Event-Driven Architectures (EDA) leveraging asynchronous stream processing for real-time reactivity.",
        body_style
    ))

    # Section 2
    story.append(Paragraph("2. Monolithic Architecture", h2_style))
    story.append(Paragraph("<b>Definition & Characteristics:</b> Packages all business capability, data access, and user interfaces into a single deployable artifact executing within a single process space backed by a central RDBMS.", body_style))
    story.append(Paragraph("<b>Advantages:</b> Simplicity of initial development, straightforward single artifact deployment (JAR, container), native ACID transactional guarantees, and simplified debugging/tracing without network hop correlation.", body_style))
    story.append(Paragraph("<b>Limitations:</b> Tight coupling and large blast radius (module crash destabilizes process), scaling bottlenecks, deployment velocity lock-in with slow regression cycles, and high cognitive onboarding load.", body_style))

    # Section 3
    story.append(Paragraph("3. Microservices Architecture", h2_style))
    story.append(Paragraph("<b>Core Principles:</b> Domain-Driven Design (single responsibility per bounded context), decentralized database-per-service data management, and independent deployability.", body_style))
    story.append(Paragraph("<b>Infrastructure Components:</b> API Gateway (TLS termination, auth, rate limiting), Service Discovery (Consul, Kubernetes DNS), Circuit Breakers (Resilience4j), and Distributed Tracing (OpenTelemetry, Jaeger).", body_style))
    story.append(Paragraph("<b>Operational Complexities:</b> Network latency, distributed transactions managed via the Saga Pattern (compensating transactions) instead of 2PC, eventual consistency, and observability overhead.", body_style))

    # Section 4
    story.append(Paragraph("4. Event-Driven Architecture (EDA)", h2_style))
    story.append(Paragraph("<b>Role:</b> Shifts microservices from synchronous request-response (HTTP/gRPC) to asynchronous publishing and consuming of state-change events using Kafka, RabbitMQ, or AWS EventBridge.", body_style))
    story.append(Paragraph("<b>Patterns:</b> Publish-Subscribe (Pub/Sub), Event Sourcing (append-only immutable log), and Command Query Responsibility Segregation (CQRS).", body_style))
    story.append(Paragraph("<b>Benefits:</b> High throughput with non-blocking I/O, temporal decoupling (consumers process backlogged messages at their own pace), high fault tolerance, and real-time streaming analytics.", body_style))

    # Section 5 Matrix
    story.append(Paragraph("5. Architectural Comparison Matrix", h2_style))
    table_data = [
        ["Dimension", "Monolithic", "Microservices", "Event-Driven (EDA)"],
        ["Complexity", "Low (single pipeline)", "High (Kubernetes)", "High (brokers, queues)"],
        ["Scalability", "Vertical/Cloning", "Per-service horizontal", "Elastic consumer groups"],
        ["Consistency", "Immediate ACID", "Eventual (Sagas)", "Eventual (stream sync)"],
        ["Team Org", "Layered (UI, DB)", "Bounded contexts", "Domain streams & contracts"],
        ["Fault Isolation", "Poor (shared process)", "Moderate (circuit breakers)", "High (message buffers)"],
    ]
    t = Table(table_data, colWidths=[90, 140, 150, 160])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    # Section 6
    story.append(Paragraph("6. Migration Strategy: Strangler Fig Pattern", h2_style))
    story.append(Paragraph("<b>Steps:</b> 1. Intercept incoming traffic via API Gateway. 2. Extract a bounded context as a standalone microservice. 3. Redirect traffic for that domain to the new service. 4. Decommission legacy monolith module iteratively.", body_style))
    story.append(Paragraph("<b>When to Stay Monolithic:</b> Engineering teams under 20-30 developers, fluid domain models, low traffic volumes, or limited distributed ops maturity.", body_style))
    story.append(Paragraph("<b>Prerequisites for Distributed Systems:</b> CI/CD automation, centralized observability (logging, metrics, tracing), and Infrastructure as Code (IaC).", body_style))

    doc.build(story)
    print(f"Generated PDF at: {output_path}")

if __name__ == "__main__":
    generate_pdf()
