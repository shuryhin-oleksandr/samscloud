SCREENING_OK_STATUS = 'OK'
SCREENING_NEED_TEST_STATUS = 'Need test'

STATUS_CHOICES = (
    (SCREENING_OK_STATUS, 'No in-person test needed at this time.'),
    (SCREENING_NEED_TEST_STATUS, 'You’re feeling ill and may need an in-person test.')
)
