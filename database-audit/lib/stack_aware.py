"""Stack-specific regex patterns for detectors. Pure data, no I/O."""

ORM_TRANSACTION_PATTERNS = {
    'prisma':           [r'\$transaction\s*\(', r'\$queryRawUnsafe', r'\$executeRaw'],
    'drizzle':          [r'\.transaction\s*\(', r'db\.transaction'],
    'typeorm':          [r'\.transaction\s*\(', r'queryRunner\.startTransaction', r'@Transaction'],
    'sequelize':        [r'sequelize\.transaction', r'\.transaction\s*\(', r'\.startTransaction'],
    'mongoose':         [r'session\.startTransaction', r'\.startTransaction\s*\('],
    'knex':             [r'\.transaction\s*\(', r'knex\.transaction'],
    'kysely':           [r'\.transaction\(\)\.execute'],
    'sqlalchemy':       [r'session\.begin', r'with\s+\w+\.begin\(\)', r'with_for_update'],
    'django-orm':       [r'transaction\.atomic', r'@transaction\.atomic'],
    'tortoise':         [r'in_transaction\s*\(', r'atomic\(\)'],
    'gorm':             [r'\.Transaction\s*\(', r'db\.Begin\s*\('],
    'sqlx':             [r'\.Beginx\s*\(', r'tx, err :=.*Begin'],
    'sqlc':             [r'\.WithTx\s*\('],
    'eloquent':         [r'DB::transaction', r'\$db->transaction'],
    'doctrine':         [r'\$em->transactional', r'->beginTransaction'],
    'activerecord':     [r'transaction\s+do', r'ActiveRecord::Base\.transaction'],
    'hibernate':        [r'@Transactional', r'session\.beginTransaction'],
    'spring-data-jpa':  [r'@Transactional'],
    'diesel':           [r'\.transaction\s*\(', r'connection\.transaction'],
}

ORM_RAW_SQL_PATTERNS = {
    'prisma':     [r'\$queryRaw', r'\$executeRaw', r'\$queryRawUnsafe', r'\$executeRawUnsafe'],
    'drizzle':    [r'sql`', r'\.execute\s*\(\s*sql'],
    'typeorm':    [r'createQueryBuilder', r'createQuery\s*\(', r'createNativeQuery'],
    'sequelize':  [r'sequelize\.query'],
    'mongoose':   [r'\.aggregate\s*\(\s*\['],
    'knex':       [r'knex\.raw', r'\.raw\s*\('],
    'sqlalchemy': [r'session\.execute', r'text\s*\(', r'\.execute\s*\(\s*text'],
    'django-orm': [r'\.raw\s*\(', r'cursor\.execute', r'connection\.cursor'],
    'gorm':       [r'\.Raw\s*\(', r'db\.Exec'],
    'sqlx':       [r'\.QueryContext', r'\.ExecContext'],
    'eloquent':   [r'DB::select', r'DB::raw', r'DB::statement'],
    'activerecord': [r'\.find_by_sql', r'connection\.execute', r'ActiveRecord::Base\.connection'],
    'hibernate':  [r'createNativeQuery', r'createQuery'],
}

ORM_LAZY_LOAD_PATTERNS = {
    'prisma':     [r'\.findMany\s*\(', r'\.findFirst\s*\(', r'\.findUnique\s*\(', r'\.findById'],
    'sequelize':  [r'\.findOne\s*\(', r'\.findAll\s*\(', r'\.findByPk'],
    'typeorm':    [r'\.findOne\s*\(', r'\.find\s*\('],
    'mongoose':   [r'\.findOne\s*\(', r'\.find\s*\(', r'\.findById'],
    'sqlalchemy': [r'\.first\s*\(\)', r'\.one\s*\(\)', r'\.all\s*\(\)', r'session\.get'],
    'django-orm': [r'\.objects\.get', r'\.objects\.filter', r'\.objects\.all'],
    'gorm':       [r'\.First\s*\(', r'\.Find\s*\('],
    'eloquent':   [r'::find\(', r'::where\(', r'::first\(\)'],
    'activerecord': [r'\.find\(', r'\.find_by', r'\.where\('],
    'hibernate':  [r'\.find\s*\(', r'session\.get'],
}

# Confidence levels for n+1 heuristic
NPLUS1_CONFIDENCE = {
    'orm_call_in_explicit_for_loop_with_iter_var': 'high',
    'orm_call_in_promise_all_map':                  'medium',
    'orm_call_in_async_iterator':                   'medium',
    'orm_call_in_loop_no_iter_dependency':          'low',
}

# Loop opener patterns by language
LOOP_PATTERNS = {
    'js_ts': [
        r'^\s*for\s*\(',
        r'^\s*for\s+\w+\s+(?:of|in)\s+',
        r'^\s*while\s*\(',
        r'\.forEach\s*\(',
        r'\.map\s*\(\s*(?:async\s*)?\(?\w+\)?\s*=>',
        r'Promise\.all\s*\(\s*\w+\.map\s*\(',
    ],
    'python': [
        r'^\s*for\s+\w+\s+in\s+',
        r'^\s*while\s+',
        r'^\s*async\s+for\s+',
    ],
    'go': [
        r'^\s*for\s+',
    ],
    'java_kotlin': [
        r'^\s*for\s*\(',
        r'\.forEach\s*\(',
        r'\.stream\(\)\.map\(',
    ],
}


def patterns_for_orm(orm, kind):
    """Return list of regex patterns for given ORM and pattern kind."""
    table = {
        'transaction': ORM_TRANSACTION_PATTERNS,
        'raw_sql':     ORM_RAW_SQL_PATTERNS,
        'lazy_load':   ORM_LAZY_LOAD_PATTERNS,
    }.get(kind, {})
    return table.get(orm, [])
