from django.contrib import admin

from .models import (
    BranchOutward,
    Grn,
    OpeningStockLine,
    OpeningStockUpload,
    OutwardInvoice,
    OutwardRegister,
    StockLedger,
)

admin.site.register(Grn)
admin.site.register(OutwardRegister)
admin.site.register(OutwardInvoice)
admin.site.register(BranchOutward)
admin.site.register(StockLedger)
admin.site.register(OpeningStockUpload)
admin.site.register(OpeningStockLine)
