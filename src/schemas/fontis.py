"""
Pydantic schemas for Fontis Water API responses.

These models match the actual Fontis API structure for validation and type safety.
All models are based on real API responses received from Fontis endpoints.
"""

from typing import Any
from pydantic import BaseModel, Field, ConfigDict


# ===== Common Models =====

class PaginationSettings(BaseModel):
    """Pagination settings for API requests."""
    Descending: bool = False
    Offset: int = 0
    OrderBy: str | None = None
    SearchText: str = ""
    Take: int = 25


class PaginationMeta(BaseModel):
    """Pagination metadata in responses."""
    offset: int
    take: int
    orderBy: str | None
    searchText: str
    descending: bool
    total: int
    hasMore: bool


class DataMeta(BaseModel):
    """Data metadata with timestamp."""
    total: int
    timestamp: str


# ===== Customer Models =====

class CustomerAddress(BaseModel):
    """Customer address information."""
    street: str
    street2: str = ""
    city: str
    state: str
    postalCode: str
    fullAddress: str


class CustomerContact(BaseModel):
    """Customer contact information."""
    phoneNumber: str = ""
    emailAddress: str = ""


class CustomerFinancial(BaseModel):
    """Customer financial summary."""
    totalDue: float
    hasScheduledDeliveries: bool


class Customer(BaseModel):
    """Customer record from search or details endpoint."""
    customerId: str
    name: str
    address: CustomerAddress
    contact: CustomerContact
    financial: CustomerFinancial


# ===== Customer Search Response =====

class CustomerSearchData(BaseModel):
    """Customer search data wrapper."""
    data: list[Customer]
    meta: DataMeta


class CustomerSearchResponse(BaseModel):
    """Complete customer search API response."""
    success: bool
    message: str
    data: CustomerSearchData
    meta: dict[str, Any]  # Contains pagination


# ===== Customer Details Response =====

class CustomerDetailsResponse(BaseModel):
    """Complete customer details API response."""
    success: bool
    message: str
    data: Customer


# ===== Invoice Models =====

class Invoice(BaseModel):
    """Invoice or payment record."""
    paginationId: str
    type: int
    invoiceNumber: str
    invoiceKey: str
    date: str  # ISO datetime string
    amount: float
    tax: float
    customerId: str
    deliveryName: str
    deliveryId: str
    viewPdf: bool
    posted: bool
    formattedAmount: str
    isPayment: bool
    isInvoice: bool


class InvoiceHistoryData(BaseModel):
    """Invoice history data wrapper."""
    data: list[Invoice]
    meta: DataMeta


class InvoiceHistoryResponse(BaseModel):
    """Complete invoice history API response."""
    success: bool
    message: str
    data: InvoiceHistoryData
    meta: dict[str, Any]  # Contains pagination


# ===== Delivery Stop Models =====

class DeliveryStopAddress(BaseModel):
    """Delivery stop address."""
    street: str
    street2: str = ""
    city: str
    state: str
    postalCode: str


class DeliveryStopContact(BaseModel):
    """Delivery stop contact information."""
    name: str = ""
    phone: str = ""
    phoneExtension: str = ""
    workPhone: str = ""
    faxPhone: str = ""
    cellPhone: str = ""
    billingEmail: str = ""
    email: str = ""


class DeliveryStopAccount(BaseModel):
    """Delivery stop account info."""
    master: str
    majorAccountCode: str = ""


class DeliveryStopDelivery(BaseModel):
    """Delivery stop delivery details."""
    route: str
    day: str
    sequence: str
    hasScheduledDeliveries: bool
    nextDeliveryDate: str | None = None
    willCall: bool
    inactive: bool


class DeliveryStopFinancial(BaseModel):
    """Delivery stop financial summary."""
    totalDue: float
    pendingPayments: float
    creditFlags: str = ""


class DeliveryStop(BaseModel):
    """Individual delivery stop record."""
    deliveryId: str
    customerId: str
    stopNumber: str
    name: str
    address: DeliveryStopAddress
    contact: DeliveryStopContact
    account: DeliveryStopAccount
    delivery: DeliveryStopDelivery
    financial: DeliveryStopFinancial
    fullAddress: str


class DeliveryStopsSummary(BaseModel):
    """Summary of all delivery stops for a customer."""
    customerId: str
    totalDeliveryStops: int
    totalDue: float
    totalPendingPayments: float
    hasScheduledDeliveries: bool
    routes: list[str]


class DeliveryStopsData(BaseModel):
    """Delivery stops data wrapper."""
    deliveryStops: list[DeliveryStop]
    summary: DeliveryStopsSummary


class DeliveryStopsResponse(BaseModel):
    """Complete delivery stops API response."""
    success: bool
    message: str
    data: DeliveryStopsData


# ===== Finance & Delivery Info Models =====

class LastPayment(BaseModel):
    """Last payment information."""
    date: str
    amount: float
    formattedAmount: str


class CustomerInfo(BaseModel):
    """Customer financial information."""
    customerId: str
    customerName: str
    billingAddress: CustomerAddress
    currentBalance: float
    pastDue: float
    oldest: str
    creditCard: str = ""
    master: str
    majorAccountCode: str = ""
    lastPayment: LastPayment
    creditFlags: list[str] = []
    hasPastDue: bool
    formattedCurrentBalance: str
    formattedPastDue: str


class DeliveryAddress(BaseModel):
    """Delivery address (same structure as CustomerAddress)."""
    street: str
    street2: str = ""
    city: str
    state: str
    postalCode: str
    fullAddress: str


class DeliveryInfo(BaseModel):
    """Delivery information details."""
    deliveryId: str
    deliveryName: str
    deliveryAddress: DeliveryAddress
    routeCode: str
    routeDay: str
    nextDeliveryDate: str | None = None
    schedulingArea: str = ""
    schedulingSubArea: str = ""
    alertMessage: str = ""
    tankInformation: str = ""
    stopImages: list[str] = []
    equipment: list[dict[str, Any]] = []
    hasScheduledDeliveries: bool


class FinanceDeliveryInfoData(BaseModel):
    """Finance and delivery info data wrapper."""
    customerInfo: CustomerInfo
    deliveryInfo: DeliveryInfo


class FinanceDeliveryInfoResponse(BaseModel):
    """Complete finance and delivery info API response."""
    success: bool
    message: str
    data: FinanceDeliveryInfoData


# ===== Billing Methods Models =====

class BillingMethod(BaseModel):
    """Payment method on file."""
    Description: str
    VaultId: str
    PayId: str
    CardExpiration: str = ""
    FeeId: str = ""
    Primary: bool
    Autopay: bool
    ProcessorExpirationDate: str | None = None


class BillingMethodsResponse(BaseModel):
    """Complete billing methods API response."""
    success: bool
    message: str
    data: list[BillingMethod]


# ===== Products Models =====

class WebClassification(BaseModel):
    """Product web classification."""
    id: str = ""
    description: str = ""
    displayLevel: int = 0
    displayOrder: list[int] = []
    parent: str = ""


class ProductBanner(BaseModel):
    """Product banner/promotion info."""
    startDate: str = ""
    endDate: str = ""
    price: float = 0
    displayOrder: int = 0
    code: str = ""


class ProductRedemptionCodes(BaseModel):
    """Product redemption codes."""
    code1: str = ""
    code2: str = ""
    code3: str = ""
    code4: str = ""


class ProductHazmat(BaseModel):
    """Product hazmat information."""
    printNSF: bool = False
    nsfMessage: str = ""
    handheldMessage: str = ""


class ProductPricing(BaseModel):
    """Product pricing details."""
    current: float
    original: float
    fixedPrice: bool = False


class Product(BaseModel):
    """Product catalog item."""
    paginationId: str = ""
    code: str
    alternateProductCode: str = ""
    description: str
    secondaryDescription: str = ""
    statementDescription: str = ""
    webDescription: str = ""
    webDescription2: str = ""
    webDescriptionLong: str = ""
    webUnitDescription: str = ""
    webDisplayOrder: int = 0
    unitDescription: str = ""
    unitsPerPackage: int = 1
    miniCode: str = ""
    productClass: str = ""
    internet: bool = False
    webClassification: WebClassification | None = None
    relatedCodes: list[str] = []
    depositType: str = ""
    depositProductList: list[str] = []
    depositProduct: str = ""
    taxCategory: str = ""
    allowGratis: bool = False
    minimumOrderQuantity: int = 0
    quantityOnHand: int = 0
    quantityAtWarehouse: int = 0
    recurring: bool = False
    branchBlackList: list[str] = []
    defaultPrice: float = 0
    webSpecial: bool = False
    banner: ProductBanner | None = None
    upc: str = ""
    nonInventory: bool = False
    baseRelationProduct: str = ""
    baseRelationQuantity: int = 0
    baseRelationLoadReference: bool = False
    productUnitReference: str = ""
    productGroup: str = ""
    redemptionProductCodes: ProductRedemptionCodes | None = None
    hazmat: ProductHazmat | None = None
    vendorPrice: float = 0
    quantityDecimals: int = 0
    suppressOnInvoice: bool = False
    showAsExtraCharge: bool = False
    prePayProductCode: str = ""
    printProductLocation: int = 0
    costPlusProductCode: str = ""
    productPricing: ProductPricing | None = None
    blackListFiltered: bool = False
    displayAlternateCode: str = ""
    formattedPrice: str = ""
    isAvailable: bool = True
    isWebSpecial: bool = False


class ProductsData(BaseModel):
    """Products data with pagination."""
    total: int
    offset: int
    took: int
    records: list[Product]


class ProductsResponse(BaseModel):
    """Complete products API response."""
    success: bool
    message: str
    data: ProductsData


# ===== Contracts Models =====

class ContractDocument(BaseModel):
    """Contract document details."""
    DocumentId: str = ""
    Description: str
    RequiresEmployeeInput: bool = False
    BaseContractTypeId: str = ""
    BaseContractTypeDescription: str = ""
    Type: int
    DocumentGuid: str
    DocumentDate: str | None = None
    FromEmail: str = ""
    ToEmails: list[str] = []
    DocumentComplete: bool = False


class Contract(BaseModel):
    """Customer contract/agreement."""
    CustomerId: str
    ContractNumber: str
    ContractType: str
    CreatedBy: str = ""
    Notes: str = ""
    SignedDate: str | None = None
    StartingDate: str
    ExpirationDate: str
    Duration: int
    UnitType: int = 0
    AuthrorizedPerson: str = ""  # Note: API has typo "Authrorized"
    AuthorizedTitle: str = ""
    ContractPrice: float = 0
    ProductCode: str = ""
    ProductDescription: str = ""
    Units: int = 0
    UnitsUsed: int = 0
    MonthlyPayments: float = 0
    GallonsType: int = 0
    Equipment: list[dict[str, Any]] = []
    Documents: list[ContractDocument] = []


class ContractsResponse(BaseModel):
    """Complete contracts API response."""
    success: bool
    message: str
    data: list[Contract]


# ===== Account Balance Models (Updated) =====

class AccountBalance(BaseModel):
    """Account balance details."""
    customerId: str
    masterAccount: str = ""
    totalDueBalance: float
    pastDueBalance: float
    onHoldBalance: float
    hasPastDue: bool
    hasOnHold: bool


class AccountBalanceResponse(BaseModel):
    """Complete account balance API response."""
    success: bool
    message: str
    data: AccountBalance


# ===== Invoice Detail Models =====

class InvoiceDetailItem(BaseModel):
    """Individual invoice line item."""
    InvoiceKey: str
    ProductCode: str
    AlternateProductCode: str = ""
    ProductDescription: str
    QuantitySold: float
    Price: float
    TaxAmount: float
    QuantityDecimalOverride: bool = False
    QuantityDecimals: int = 0
    BeginningReadings: float = 0
    EndingReadings: float = 0
    EquipmentSerialNumber: str = ""
    GratisReasonCode: str = ""
    FromFullQuantity: float = 0
    Increase: float = 0
    Level: str = "0"
    NextDeliveryDate: str | None = None
    NonTankQuantity: float = 0
    OrderReductionCode: str = ""
    PackagePlanProduct: bool = False
    PAROriginal: float = 0
    PARReported: float = 0
    PARNew: float = 0
    PARModified: bool = False
    PrePayQuantityAvailable: float = 0
    ProductSerialNumber: str = ""
    PurchaseOrderNumber: str = ""
    ReturnCode: str = ""
    Returns: float = 0
    TaxAmount1: float = 0
    TaxAmount2: float = 0
    TaxAmount3: float = 0
    TaxAmount4: float = 0
    TaxAmount5: float = 0
    TaxAmount6: float = 0
    TaxCode: str = ""
    TaxExemptAmount: float = 0
    Weight: float = 0
    ProductClassCode: str = ""
    DepositCode: str = ""
    ProductGroupCode: str = ""


class InvoiceDetail(BaseModel):
    """Complete invoice detail."""
    PaginationId: str | None = None
    InvoiceKey: str
    InvoiceNumber: str
    InvoiceDate: str
    BranchId: str
    AccountNumber: str
    DeliveryStopId: str
    CustomerStopNumber: int
    CustomerName: str
    CreditClass: str = ""
    ContactName: str = ""
    ContactPhone: str = ""
    CustomerEmailAddress: str = ""
    InvoiceType: int
    TicketNumber: str
    CustomerAddress: str
    CustomerCity: str
    CustomerState: str
    CustomerPostalCode: str
    Latitude: float = 0
    Longitude: float = 0
    Posted: bool
    RouteCode: str
    SubTotal: float
    TaxAmount: float
    AgingLevel1: float = 0
    AgingLevel2: float = 0
    AgingLevel3: float = 0
    AgingLevel4: float = 0
    AgingLevel5: float = 0
    AgingLevel6: float = 0
    AccountBalance: float
    AdditionalAccountNumber: str = ""
    DeliveryNote: str = ""
    Comments: str = ""
    SalesTaxCode: str = ""
    DriverInitials: str = ""
    Signature: str | None = None
    SigneeName: str = ""
    PurchaseOrderNumber: str = ""
    InvoiceDetails: list[InvoiceDetailItem]
    InvoicePayments: list[dict[str, Any]] = []


class InvoiceDetailResponse(BaseModel):
    """Complete invoice detail API response."""
    success: bool
    message: str
    data: InvoiceDetail


# ===== Off-Route Orders Models =====

class OrderProduct(BaseModel):
    """Product in an order."""
    Code: str
    AlternateProductCode: str = ""
    CouponApplied: bool = False
    Description: str
    WebDescription: str = ""
    WebDescription2: str = ""
    WebDescriptionLong: str = ""
    Quantity: int
    Price: float
    OriginalPrice: float
    MinimumOrderQuantity: int = 0
    FillUp: bool = False
    FixedPrice: bool = False
    Taxable: bool = True
    Gratis: str = ""


class DeliveryOrder(BaseModel):
    """Off-route delivery order."""
    DeliveryId: str
    DeliveryDate: str
    DeliveryNote: str = ""
    FullDeliveryNote: str = ""
    TicketNumber: str
    Branch: str
    Route: str
    Products: list[OrderProduct]
    Equipment: list[dict[str, Any]] = []
    WebCoupon: dict[str, Any] | None = None
    ExactType: int = 0
    ExactDate: str = ""
    ExactTime: str | None = None
    HighPriority: bool = False
    PONumber: str = ""


class OrdersMeta(BaseModel):
    """Orders metadata."""
    customerId: str
    deliveryId: str
    totalOrders: int
    totalAmount: float


class OrdersResponse(BaseModel):
    """Complete orders API response."""
    success: bool
    message: str
    data: list[DeliveryOrder]
    meta: OrdersMeta


# ===== Delivery Frequencies Models =====

class DeliveryFrequenciesResponse(BaseModel):
    """Delivery frequencies API response."""
    success: bool
    message: str
    data: list[dict[str, Any]]  # Empty for now based on response


# ===== Default Products Models =====

class DefaultProduct(BaseModel):
    """Default product for delivery stop."""
    productCode: str | None = None
    productName: str | None = None
    quantity: int = 0
    defaultQuantity: int = 0
    description: str | None = None


class DefaultProductsMeta(BaseModel):
    """Default products metadata."""
    deliveryId: str
    totalProducts: int
    activeProducts: int


class DefaultProductsResponse(BaseModel):
    """Complete default products API response."""
    success: bool
    message: str
    data: list[DefaultProduct]
    meta: DefaultProductsMeta


# ===== Next Scheduled Delivery Models =====

class SearchRange(BaseModel):
    """Search range for next delivery."""
    from_: str = Field(alias="from")
    to: str
    daysAhead: int
    
    model_config = ConfigDict(populate_by_name=True)


class NextDeliveryMeta(BaseModel):
    """Next delivery metadata."""
    customerId: str
    deliveryId: str
    searchRange: SearchRange
    upcomingDeliveries: int


class NextDelivery(BaseModel):
    """Next scheduled delivery."""
    date: str
    formatted: str
    dayOfWeek: str
    deliveryRoute: str
    deliveryId: str
    calendarType: int
    ticketNumber: str
    enableEditing: bool


class NextDeliveryResponse(BaseModel):
    """Complete next delivery API response."""
    success: bool
    message: str
    data: NextDelivery
    meta: NextDeliveryMeta


# ===== Credit Card Vault Models =====

class CreditCardVaultData(BaseModel):
    """Credit card vault response data."""
    vaultId: str
    payId: str
    lastFour: str
    success: bool
    message: str
    gatewayResponseCode: int
    processorResponseCode: str


class CreditCardVaultResponse(BaseModel):
    """Complete credit card vault API response."""
    success: bool
    message: str
    data: CreditCardVaultData


# ===== Orders Search Models =====

class OrderSearchResult(BaseModel):
    """Individual order search result - placeholder for actual data structure."""
    # Based on response showing empty objects, structure TBD
    pass


class OrdersSearchResponse(BaseModel):
    """Complete orders search API response."""
    success: bool
    message: str
    data: list[dict[str, Any]]  # Flexible structure until exact format known


# ===== Route Stops Models =====

class RouteStop(BaseModel):
    """Individual route stop details."""
    accountNumber: str
    branch: str
    calendarId: str
    calendarSequence: str
    calendarType: int
    customerAddress: str
    customerCity: str
    customerName: str
    customerPostalCode: str
    customerState: str
    deliveryId: str
    highPriority: bool
    invoiceDate: str | None = None
    invoiceKey: str = ""
    invoiceTotal: float = 0
    invoiceType: int = 0
    latitude: float = 0
    longitude: float = 0
    numberOfDrags: int = 0
    overrideDragWithSequence: bool = True
    paginationId: str | None = None
    routeCode: str
    scheduleDate: str
    scheduleType: int = 0
    skipReason: str = ""
    ticketNumber: str = ""


class RouteStopsResponse(BaseModel):
    """Complete route stops API response."""
    success: bool
    message: str
    data: list[RouteStop]
