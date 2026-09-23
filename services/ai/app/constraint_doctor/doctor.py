from app.schemas.models import ConstraintDoctorRequest, ConstraintDoctorResponse


_STAGE_LABELS = {
    "category": "всего в категории",
    "city": "работают в выбранном городе",
    "available_date": "свободны на выбранную дату",
    "format": "подходят по формату",
    "budget": "подходят по бюджету",
    "language": "подходят по языку",
    "duration": "подходят по длительности",
}


def diagnose_constraints(request: ConstraintDoctorRequest) -> ConstraintDoctorResponse:
    ordered_keys = list(_STAGE_LABELS)
    funnel = [
        {"stage": key, "label": _STAGE_LABELS[key], "count": max(0, request.counts.get(key, 0))}
        for key in ordered_keys
        if key in request.counts
    ]
    values = {str(item["stage"]): int(item["count"]) for item in funnel}
    category_count = values.get("category", 0)
    city_count = values.get("city", 0)
    final_count = values.get("duration", values.get("language", values.get("budget", values.get("format", values.get("available_date", city_count)))))

    if category_count > 0 and city_count == 0:
        return ConstraintDoctorResponse(
            outcome="category_absent_in_city",
            summary=f"В категории «{request.category}» есть {category_count} профилей, но в городе {request.city} подходящих нет.",
            funnel=funnel,
            primary_blocker="city",
        )

    if final_count > 0:
        return ConstraintDoctorResponse(
            outcome="matched",
            summary=f"После проверки условий осталось {final_count} подходящих кандидатов.",
            funnel=funnel,
        )

    blocker = next(
        (key for key in ordered_keys[1:] if key in values and values[key] == 0),
        "constraints",
    )
    explanations = {
        "available_date": "кандидаты есть, но они заняты на выбранную дату",
        "format": "ни один кандидат не берёт выбранный формат",
        "budget": (
            f"минимальная цена {request.minimum_price:,} ₸ выше бюджета {request.requested_budget:,} ₸".replace(",", " ")
            if request.minimum_price is not None and request.requested_budget is not None
            else "ни один кандидат не проходит ограничение по бюджету"
        ),
        "language": "ни один кандидат не работает на выбранном языке",
        "duration": "ни один кандидат не подходит по длительности",
        "constraints": "кандидаты не прошли заданные условия",
    }
    return ConstraintDoctorResponse(
        outcome="constraints_failed",
        summary=f"В категории «{request.category}» найдены кандидаты, но {explanations[blocker]}.",
        funnel=funnel,
        primary_blocker=blocker,
    )
