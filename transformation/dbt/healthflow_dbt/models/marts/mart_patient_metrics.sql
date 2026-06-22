with encounters as (
    select * from {{ ref('stg_encounters') }}
),

conditions as (
    select * from {{ ref('stg_conditions') }}
),

medications as (
    select * from {{ ref('stg_medications') }}
),

patients as (
    select * from {{ ref('stg_patients') }}
),

encounter_metrics as (
    select
        patient_id,
        count(*)                        as total_encounters,
        sum(total_claim_cost)           as total_claim_cost,
        avg(total_claim_cost)           as avg_claim_cost,
        sum(out_of_pocket)              as total_out_of_pocket,
        min(encounter_date)             as first_encounter_date,
        max(encounter_date)             as last_encounter_date,
        countif(encounter_class = 'emergency') as emergency_visits
    from encounters
    group by patient_id
),

condition_metrics as (
    select
        patient_id,
        count(*)                        as total_conditions,
        countif(is_chronic = true)      as chronic_conditions
    from conditions
    group by patient_id
),

medication_metrics as (
    select
        patient_id,
        count(*)                        as total_medications,
        countif(is_active = true)       as active_medications,
        sum(total_cost)                 as total_medication_cost
    from medications
    group by patient_id
),

final as (
    select
        p.patient_id,
        p.gender,
        p.race,
        p.ethnicity,
        p.state,
        p.age_years,
        p.age_group,
        p.is_deceased,
        coalesce(em.total_encounters, 0)      as total_encounters,
        coalesce(em.total_claim_cost, 0)      as total_claim_cost,
        coalesce(em.avg_claim_cost, 0)        as avg_claim_cost,
        coalesce(em.total_out_of_pocket, 0)   as total_out_of_pocket,
        coalesce(em.emergency_visits, 0)      as emergency_visits,
        em.first_encounter_date,
        em.last_encounter_date,
        coalesce(cm.total_conditions, 0)      as total_conditions,
        coalesce(cm.chronic_conditions, 0)    as chronic_conditions,
        coalesce(mm.total_medications, 0)     as total_medications,
        coalesce(mm.active_medications, 0)    as active_medications,
        coalesce(mm.total_medication_cost, 0) as total_medication_cost
    from (
        select
            p.*,
            case
                when p.age_years < 18 then 'pediatric'
                when p.age_years < 65 then 'adult'
                else 'senior'
            end as age_group
        from patients p
    ) p
    left join encounter_metrics  em on p.patient_id = em.patient_id
    left join condition_metrics  cm on p.patient_id = cm.patient_id
    left join medication_metrics mm on p.patient_id = mm.patient_id
)

select * from final
