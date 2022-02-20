
from django.http.response import JsonResponse
from django.shortcuts import redirect, render
from pymysql import NULL
from .forms import RegistrationForm, add_address, logForm, NumberOnly, OTPField
from django.contrib.auth import authenticate
from .models import CustomUser, address, cart, order, whishlist
from .verification import check, SendOTP
from adminApp.models import *
from django.db.models import Q, Sum
# from decouple import config
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.cache import never_cache
from ecom.settings import api_key, api_secret
import razorpay
client = razorpay.Client(auth=(api_key, api_secret))


# =============================================================================
"""
guest user functionality. using browser session for identify user. return the 
browser session id if dont have create the id
"""

def GetGuestUser(request):
    key = request.session.session_key
    if not key:
        request.session.create()
    return key



# =============================================================================
"""
after user logged in and if user added products into cart as a guset user
set foreign key into the user_id field and delete browser session id
and if the products alredy in the user id the quantity increse accordingly
"""

def MoveGuestToUser(request):
    cartItems = cart.objects.filter(guest_user=GetGuestUser(request))
    u = CustomUser.objects.get(username=request.session['user'])

    for items in cartItems:
        if cart.objects.filter(Q(user_id=u) & Q(variant_id=items.variant_id)).exists():
            a = cart.objects.get(Q(user_id=u) & Q(variant_id=items.variant_id))
            a.quantity = items.quantity + a.quantity
            a.subtotal = items.subtotal + a.subtotal
            a.save()
            items.delete()

    cartItems.update(user_id=u, guest_user=NULL)



# =============================================================================
# get all category data for reuse

def GetCategory():
    cat = Category.objects.all()
    return cat



# =============================================================================
"""
finding the user if user is online or offline or blocked.
if blocked delete the session so user will automatically logout
"""

def foundUser(request):
    if 'user' in request.session:
        u = CustomUser.objects.get(username=request.session['user'])
        if u.block == True:
            del request.session['user']
            return False
        return True
    return False



# =============================================================================
# count cart items of user or guest user for display in the header

def countItems(request):
    try:
        count = cart.objects.filter(
            user_id__username=request.session['user']).count()
    except:
        count = cart.objects.filter(guest_user=GetGuestUser(request)).count()
    return count



# =============================================================================
# find subtotal

def FindSubTotal(request):
    try:
        usersProduct = cart.objects.filter(user_id__username=request.session['user']).values(
            'quantity', 'variant_id__quantity', 'subtotal')
    except:
        usersProduct = cart.objects.filter(guest_user=GetGuestUser(request)).values(
            'quantity', 'variant_id__quantity', 'subtotal')

    cart_subtoal = 0
    for i in usersProduct:
        if i['quantity'] <= i['variant_id__quantity']:
            cart_subtoal += i['subtotal']
    return cart_subtoal


# =============================================================================
# register page view

def register(request):
    if foundUser(request):
        return redirect('/')
    reg_form = RegistrationForm(request.POST or None)

    context1 = {
        'session': foundUser(request),
        'category': GetCategory(),
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values(
            'id', 'c_id__id', 'c_id__id', 'brand_name'),
    }

    if request.method == "POST":
        if reg_form.is_valid():
            data = reg_form.cleaned_data
            num = "+91" + data['number']
            try:       

                # --------------------------------------------------------------------    
                # sending otp   
                # --------------------------------------------------------------------  

                SendOTP(num)    
                request.session['num'] = data['number']
                f = reg_form.save(commit=False)
                f.is_active = 0
                f.save()
                return redirect('OTP_register')
            except:      

                # --------------------------------------------------------------------  
                # if user entered a wrong number twillio throw error. and return a messege to user to enter valid number   
                # --------------------------------------------------------------------  

                context2 = {'form': reg_form,
                            'url': 'register',
                            'err': 'enter valid number'}
                context = {**context1, **context2}
                return render(request, 'userTempl/register.html', context)
    context2 = {
        'form': reg_form,
        'url': 'register',
        'whishlist_count': GetCountWhishlist(request)

    }
    context = {**context1, **context2}
    return render(request, 'userTempl/register.html', context)



# =============================================================================
# login page view

@never_cache
def login(request):
    if foundUser(request):
        return redirect('/')

    err = ''

    if request.method == "POST":
        form = logForm(request.POST)
        if form.is_valid():
            u_name = request.POST['username']
            u_pwd = request.POST['password']
            user = authenticate(username=u_name, password=u_pwd)
            if user is not None:
                ck = CustomUser.objects.get(username=u_name)
                if ck.block == 0:
                    request.session['user'] = u_name

                    if cart.objects.filter(guest_user=GetGuestUser(request)).exists():

                        # ======================================================================================
                        """
                        if user added product to cart as guset user these items move to user id and delete the session
                        id used in verify the the user
                        """
                        MoveGuestToUser(request)
                        # ======================================================================================


                    return redirect('/')
                else:
                    err = 'you are blocked'
            else:
                err = 'user not found'
    else:
        form = logForm()

    context = {
        'session': foundUser(request),
        'category': GetCategory(),
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values(
            'id', 'c_id__id', 'c_id__id', 'brand_name'),
        'form': form,
        'err': err,
        'whishlist_count': GetCountWhishlist(request)
    }
    return render(request, 'userTempl/login.html', context)



# =============================================================================
# send otp using twilio

@never_cache
def NumberField(request):
    if foundUser(request):
        return redirect('/')

    form = NumberOnly(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            getNum = request.POST['mobile_number']
            num = "+91" + getNum

            # send otp function
            SendOTP(num)
            
            request.session['numberLog'] = getNum
            return redirect('enter_otp')
    context = {
        'session': foundUser(request),
        'category': GetCategory(),
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'form': form,
        'whishlist_count': GetCountWhishlist(request)
    }

    return render(request, "userTempl/enter_num.html", context)



# =============================================================================
# get otp from  user and check with the number  if the opt user entered correct or not

@never_cache
def EnterOtp(request):
    if foundUser(request):
        return redirect('/')
    err = ''
    form = OTPField(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            otp = request.POST['OTP']
            num = "+91" + request.session['numberLog']
            res = False
            try:
                res = check(otp, num)  # check the otp user enterd
                
            except:
                pass
            if res:
                user = authenticate(number=num)
                u = CustomUser.objects.get(number=request.session['numberLog'])

                username = u.username
                request.session['user'] = username
                MoveGuestToUser(request)

                del request.session['numberLog']

                return redirect("home")
            else:
                err = "not a valid otp"
    context = {
        'session': foundUser(request),
        'category': GetCategory(),
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'form': form,
        'err': err,
        'url': '/enter_otp',
        'number': request.session['numberLog'],
        'whishlist_count': GetCountWhishlist(request)
    }
    return render(request, "userTempl/enter_otp.html", context)




# =============================================================================
# check the otp user entered after user fill the registration form

@never_cache
def OTPRegister(request):
    if foundUser(request):
        return redirect('/')

    err = ''
    form = OTPField(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if form.is_valid():
            otp = request.POST['OTP']
            n = "+91" + request.session['num']
            if check(otp, n):
                u = CustomUser.objects.get(number=request.session['num'])
                u.is_active = 1
                u.save()
                del request.session['num']
                request.session['user'] = u.username

                if cart.objects.filter(guest_user=GetGuestUser(request)).exists():

                    # move cart item guest user added 
                    MoveGuestToUser(request)

                return redirect("home")
            else:
                err = "not a valid otp"

    context = {
        'number': request.session['num'],
        'form': form,
        'err': err,
        'url': '/OTP_register',
        'session': foundUser(request),
        'category': GetCategory(),
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'whishlist_count': GetCountWhishlist(request)
    }

    return render(request, "userTempl/enter_otp.html", context)



# =============================================================================
# get count of user whishlist if user is in the session

def GetCountWhishlist(request):
    return whishlist.objects.filter(user_id__username=request.session['user']).count() if 'user' in request.session else 0



# =============================================================================
# home  page with data latest and popular product

@never_cache
def home(request):
    latest = []
    byCategory = []
    avilable_cat = []
    count = 0
    p = products.objects.all().order_by('-date').select_related('product_id__brand_id').select_related('product_id__brand_id__c_id')

    for i in Category.objects.all():

        filterProduct = p.filter(brand_id__c_id=i).order_by('-date').values('id')


        for a in filterProduct:

            count += 1
            variants = VariantAndPrice.objects.filter(product_id__id=a['id']).select_related(
                'product_id').select_related('product_id__brand_id').select_related('product_id__brand_id__c_id')
            
            # ---------------------------------------------------------------------------
            """
            every product have 2 variant it will diaply according which product have least ram.
            is the produt have least ram is out of stock the other varaint is going to display
            """
            temp = variants[0]
            if variants[0].quantity == 0 and variants[1].quantity > 0:
                temp = variants[1]
            # --------------------------------------------------------------------------------
            
            if i not in avilable_cat:
                avilable_cat.append(i)

            byCategory.append(temp)
            latest.append(temp)
            if count == 4:
                break


    context = {
        'latest': latest[:4],
        'session': foundUser(request),
        'category': GetCategory(),
        'banner': Banner.objects.all().select_related('p_id'),
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'bycategory': byCategory,
        'whishlist_count': GetCountWhishlist(request),
        'avilable_cat': avilable_cat
    }
    return render(request, 'userTempl/sampleHome.html', context)



# =============================================================================
# showing the product user clicked in the each product page

def eachproduct(request):

    vari = VariantAndPrice.objects.filter(product_id=request.GET['p_id']).select_related(
        'product_id'
    ).select_related(
            'product_id__brand_id'
    ).order_by('variant')

    prod = products.objects.filter(id=request.GET['p_id'])

    context = {
        'product': prod,
        'variants': vari,
        'varinat1': vari[0],
        'session': foundUser(request),
        'category': GetCategory(),
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'whishlist_count': GetCountWhishlist(request)
    }

    return render(request, 'userTempl/eachproduct.html', context)



# =============================================================================
# user logout view also delete the user session

def UserLogout(request):
    if foundUser(request):
        del request.session['user']
    return redirect('/')



# =============================================================================
# covert string into listfor product filtering. data passed  as string from html form. coverting into list for giving in orm

def splitString(request, inp):
    temp = request.GET[inp].split(',')
    for i in range(len(temp)):
        try:
            temp[i] = int(temp[i])
        except:
            temp[i] = temp[i]
    return temp



# =============================================================================
"""
get product variant according to quantity. if one varaint is out of stock get it will return another variant for lsiting 
product data in the home page and product list page
"""

def ReturnList(prod):
    vari = []
    for i in prod:
        allVari = VariantAndPrice.objects.filter(product_id=i)
        vari += [allVari[0]] if allVari[0].quantity else [allVari[1]]
    return vari



# =============================================================================
"""
listing all product in this page . also included product sorting  option .
"""

@never_cache
def ProductList(request):
    minBool = False
    sort_by_category = request.GET.get('c_id' or 0)
    sort_by_subcategory = request.GET.get('sub_id' or 0)
    min = request.GET.get('min' or 0)

    vari = []

    if sort_by_category:
        prod = products.objects.filter(
            brand_id__c_id__id=sort_by_category).values_list('id')
        vari = ReturnList(prod)

    elif sort_by_subcategory:
        prod = products.objects.filter(
            brand_id__id=sort_by_subcategory).values_list('id')
        vari = ReturnList(prod)

    elif min:
        minBool = True
        category = splitString(request, 'category')
        brand = splitString(request, 'brand')
        ramIs = splitString(request, 'ram')
        processor = splitString(request, 'processor')


        # --------------------------------------------------------------------------------
        """
        filtering of the product according to brand, os , price, processor and ram. all the user input is given as list 
        """

        vari = VariantAndPrice.objects.filter(
            Q(product_id__brand_id__c_id__id__in=category) &
            Q(product_id__brand_id__id__in=brand) &
            Q(variant__in=ramIs) &
            Q(price__gte=request.GET['min']) &
            Q(price__lte=request.GET['max']) &
            Q(product_id__processor__in=processor) 
        ).all()

        # --------------------------------------------------------------------------------


    else:
        prod = products.objects.values_list('id').all()
        vari = ReturnList(prod)

    paginator = Paginator(vari, 6)
    page = request.GET.get('page')
    pageUrl = request.build_absolute_uri().replace('page='+str(page), '')
    try:
        a = paginator.page(page)
    except PageNotAnInteger:
        a = paginator.page(1)
    except EmptyPage:
        a = paginator.page(paginator.num_pages)

    context = {
        'allProducts': a,
        'category': Category.objects.all(),
        'ram': VariantAndPrice.objects.values("variant").distinct(),
        'processor': VariantAndPrice.objects.values("product_id__processor").distinct(),
        'brand': SubCategory.objects.all(),
        'session': foundUser(request),
        'cart_count': countItems(request),
        'page': page,
        'pageUrl': pageUrl,
        'minBool': minBool,
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'whishlist_count': GetCountWhishlist(request)
    }
    return render(request, 'userTempl/product-grids.html', context)



# =============================================================================
# add to cart using ajax request

def AddToCart(request):
    varaintIs = VariantAndPrice.objects.get(id=request.GET['vari_id'])
    if foundUser(request):
        u = CustomUser.objects.get(username=request.session['user'])
        c = cart.objects.filter(Q(user_id=u) & Q(variant_id=varaintIs))
        if not c.exists():
            c.create(
                user_id=u, variant_id=varaintIs,
                subtotal=varaintIs.final_price
            )
        return JsonResponse(
            {'success': True, 'cart_count': countItems(request)},
            safe=False
        )
    else:
        if not cart.objects.filter(Q(guest_user=GetGuestUser(request)) & Q(variant_id=varaintIs)).exists():
            cart.objects.create(
                guest_user=GetGuestUser(request),
                variant_id=varaintIs,
                subtotal=varaintIs.final_price
            )
        return JsonResponse(
            {'success': True, 'cart_count': countItems(request)},
            safe=False
        )


# checks if the product offer changed if changed change price accordingly
def isChanged(request):
    try:
        c = cart.objects.filter(
            user_id__username=request.session['user']).select_related(
                'variant_id'
        )
    except:
        c = cart.objects.filter(
            guest_user=GetGuestUser(request)).select_related(
                'variant_id'
        )
    for a in c:
        # off = 0
        if a.variant_id.final_price != a.subtotal / a.quantity:
            a.subtotal = a.variant_id.final_price * a.quantity
            a.save()



# =============================================================================
# on click  the cart button go to cart

@never_cache
def myCart(request):
    if foundUser(request):
        isChanged(request)
        items = cart.objects.filter(user_id__username=request.session['user'])
    else:
        items = cart.objects.filter(guest_user=GetGuestUser(request))

    context = {
        'cartItems': items,
        'session': foundUser(request),
        'cart_sub': FindSubTotal(request),
        'category': GetCategory,
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'whishlist_count': GetCountWhishlist(request)
    }
    return render(request, 'userTempl/cart.html', context)



# =============================================================================
# change quatity of the product from the cart

def ChangeQuantity(request):
    c_id = request.GET['c_id']
    type = request.GET['type']
    cart_data = cart.objects.get(id=c_id)
    err = 'success'
    sub = 0
    if cart_data.quantity < cart_data.variant_id.quantity and 1 == int(type) or int(type) == -1 and cart_data.quantity > 1:

        cart_data.quantity = cart_data.quantity + int(type)
        q = cart_data.quantity
        cart_data.subtotal = cart_data.variant_id.final_price * cart_data.quantity
        sub = cart_data.subtotal
        cart_data.save()
        return JsonResponse(
            {'success': True, 'quantity': q, 'subtotal': sub,'cart_subtotal': FindSubTotal(request), 'err': err},
            safe=False
        )
    return JsonResponse(
        {'success': False, 'err': 'fails'},
        safe=False
    )



# =============================================================================
# remove items added in cart

def removeIremFromCart(request):
    cart_id = request.GET["c_id"]
    cart.objects.filter(id=cart_id).delete()
    return JsonResponse(
        {'success': True, 'cart_subtotal': FindSubTotal(
            request), 'cartCount': countItems(request)},
        safe=False
    )



# =============================================================================
# checkout page. check the user wants to buy the products form the cart or the buy now 

@never_cache
def Checkout(request, id=0):
    if 'user' not in request.session:
        return redirect('login')
    isChanged(request)

    context = {}
    context2 = {}
    form = add_address()
    addresses = address.objects.filter(user_id__username=request.session['user']
    ).order_by("-id").values('full_name', 'city', 'mobile_number', 'zipcode', 'address', 'id')
    context1 = {
        'form': form,
        'url': '/addressForm',
        'addresses': addresses,
        'session': foundUser(request),
        'category': Category.objects.all(),
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'whishlist_count': GetCountWhishlist(request)

    }

    # if the received id is 0 it will assumed as user clicked the cart checkout button
    if int(id) == 0:
        context2 = {
            'cartItems': cart.objects.filter(
                user_id__username=request.session['user']).values(
                    'variant_id__price',
                    'variant_id__final_price',
                    'variant_id__product_id__offer',
                    'variant_id__product_id__brand_id__c_id__offer',
                    'variant_id__product_id__product_name',
                    'variant_id__product_id__brand_id__brand_name',
                    'quantity',
                    'variant_id__quantity',
                    'subtotal'
            ),
            'cart_subtotal': FindSubTotal(request),
            'from': id
        }
        context2['raz_amt'] = context2['cart_subtotal'] * 100


    elif int(id) > 0:
        # ..................................................................................................
        """
        # if user clicked the buy now option the varaint id will be pass. definately the value is greater than 0.
        # so programm asume that user is cliked buy now
        """
        v = VariantAndPrice.objects.get(id=id)
        context2 = {
            'items': v,
            'buynow': True,
            'from': id,
            'whishlist_count': GetCountWhishlist(request)
        }
        context2['raz_amt'] = v.final_price * 100
        # ..................................................................................................

    context = {**context1, **context2}

    r = int(context['raz_amt'])
    request.session['raz_amt'] = r
    return render(request, 'userTempl/checkout.html', context)



# =============================================================================
# validating address form placed in checkout page

def addressForm(request):
    form = add_address(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            f = form.save(commit=False)
            f.user_id = CustomUser.objects.get(
                username=request.session['user'])
            f.save()
            return JsonResponse(
                {'success': True},
                safe=False
            )
    return JsonResponse(
        {'success': False},
        safe=False
    )



# =============================================================================
"""
order placed view. transfer value form products table to order table.
this is only for if the usr buy the products added in cart
"""

def CartCalc(request, address_id, payMethod, coupenId=0):
    limit = 0
    u_id = CustomUser.objects.get(username=request.session['user'])
    cartItems = cart.objects.filter(user_id=u_id)

    coupenData = 0

    if coupenId:
        coupenData = Coupen.objects.get(id=coupenId)
    for i in cartItems:

        # produts are out of stock or the order qty more than orginal produts qty this produts excluding in purchasing
        if i.quantity <= i.variant_id.quantity and not i.variant_id.quantity <= 0: 

            addr = address.objects.get(id=address_id)
            addre = 'Full name: ' + str(addr.full_name) + ' address: ' + str(addr.address) + ' city: ' + str(
                addr.city) + ' pincode: ' + str(addr.zipcode) + ' mobile: ' + str(addr.mobile_number)

            if coupenId:
                subtotal = i.subtotal - \
                    (i.subtotal * coupenData.coupen_offer) / 100
                order.objects.create(total_qty=i.quantity,  address=addre, userId=u_id,
                                     variant_id=i.variant_id, payment_method=payMethod,
                                     subtotal=subtotal, coupen_id=coupenData)

            else:
                order.objects.create(total_qty=i.quantity,  address=addre, userId=u_id,
                                     variant_id=i.variant_id, payment_method=payMethod,
                                     subtotal=i.subtotal)

            v = VariantAndPrice.objects.filter(id=i.variant_id_id).update(
                quantity=i.variant_id.quantity - i.quantity)
            i.delete()
            limit += 1
    return limit



# =============================================================================
# set values into order palced table in the case of buy now.

def BuyNowCalc(request, address_id, payMethod, coupenId=0):
    v = request.POST['variant']
    u_id = CustomUser.objects.get(username=request.session['user'])
    coupenData = 0

    if coupenId:
        coupenData = Coupen.objects.get(id=coupenId)

    i = VariantAndPrice.objects.get(id=v)
    addr = address.objects.get(id=address_id)
    addre = 'Full name: ' + str(addr.full_name) + ' address: ' + str(addr.address) + ' city: ' + str(
        addr.city) + ' pincode: ' + str(addr.zipcode) + ' mobile: ' + str(addr.mobile_number)
    i.quantity = i.quantity - 1
    orders = order()
    orders.total_qty = 1
    orders.address = addre
    orders.userId = u_id
    orders.variant_id = i
    orders.payment_method = payMethod
    if coupenId:
        orders.subtotal = i.final_price - \
            (i.final_price * coupenData.coupen_offer) / 100
        orders.coupen_id = coupenData
    else:
        orders.subtotal = i.final_price
    orders.save()
    i.save()
    return 1



# =============================================================================
# passing order details set data in order table. finding which option user choosen and redirect to corrent function

def MakePayment(request):
    payMethod = request.POST['paymentMethod']
    address_id = request.POST['addressId']
    buyOrCart = request.POST['from']
    coupenId = request.POST.get('coupenId' or 0)

    if buyOrCart == "cart":
        limit = CartCalc(request, address_id, payMethod, coupenId) # funtion for products buyed from cart
    else:
        limit = BuyNowCalc(request, address_id, payMethod, coupenId) # funtion if user buyed using buy now option

    return redirect('/invoice/'+str(limit))



# =============================================================================
# cancell and return from order deatails page

def CancellOreturn(request):

    val = request.GET['val']
    ord = order.objects.get(id=request.GET['id'])
    if val == "Cancel":
        ord.order_status = "Cancelled" 
    else:
        ord.order_status = "Returned"

    v_id = ord.variant_id
    vari = VariantAndPrice.objects.get(id=v_id.id)
    vari.quantity = vari.quantity + 1
    vari.save()
    ord.save()

    return JsonResponse(
        {'success': True},
        safe=False
    )



# =============================================================================
# search bar

def Search(request):
    p = products.objects.filter(product_name__icontains=request.GET['input'])
    vari = []
    for i in p:
        vari += [VariantAndPrice.objects.filter(product_id=i)[0]]
    context = {
        'allProducts': vari,
        'brand': SubCategory.objects.all(),
        'ram': VariantAndPrice.objects.values("variant").distinct(),
        'session': foundUser(request),
        'category': Category.objects.all(),
        'brand': SubCategory.objects.all(),
        'session': foundUser(request),
        'cart_count': countItems(request),
        'whishlist_count': GetCountWhishlist(request)
    }
    return render(request, 'userTempl/product-grids.html', context)



# =============================================================================
# profile page

@never_cache
def Profile(request):
    if 'user' not in request.session:
        return redirect('login')
    form = add_address()
    user = CustomUser.objects.get(username=request.session['user'])
    context = {
        'user': user,
        'address': address.objects.filter(user_id=user).order_by("-id"),
        'session': foundUser(request),
        'form': form,
        'cart_count': countItems(request),
        'category': Category.objects.all(),
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'whishlist_count': GetCountWhishlist(request)
    }
    return render(request, 'userTempl/profile.html', context)



# =============================================================================
# edit profile info 

def EditProfile(request):
    err_username = ''
    err_email = ''
    err_number = ''
    good = 0

    first_name = request.POST['first_name']
    last_name = request.POST['last_name']
    username = request.POST['username']
    email = request.POST['email']
    number = request.POST['number']

    if request.method == "POST":
        if username != request.session['user'] and CustomUser.objects.filter(username=username).exists():
            err_username = 'username alredy exist'
            good += 1

        if CustomUser.objects.filter(email=email).exclude(username=request.session['user']).exists():
            err_email = 'email exist'
            good += 1

        if CustomUser.objects.filter(number=number).exclude(username=request.session['user']).exists():
            err_number = 'number alredy exist'
            good += 1

        if good == 0:
            u_id = CustomUser.objects.filter(username=request.session['user'])
            u_id.update(
                first_name=first_name, last_name=last_name, username=username, email=email, number=number)
            return JsonResponse(
                {'success': True},
                safe=False
            )
        return JsonResponse(
            {'success': False, 'username': err_username,
                'email': err_number, 'number': err_number},
            safe=False
        )



# =============================================================================
# change password option in profile 

def ChangePassword(request):

    old_pwd = request.POST['old_pwd']
    new_pwd = request.POST['new_pwd']

    if request.method == "POST":
        user = authenticate(username=request.session['user'], password=old_pwd) # validating the previous password with authenticate method
        if user:
            u = CustomUser.objects.get(username=request.session['user'])
            u.set_password(new_pwd)
            u.save()

            return JsonResponse(
                {'success': True},
                safe=False
            )
        return JsonResponse(
            {'success': False},
            safe=False
        )



# =============================================================================
# edit address details

def EditAddress(request):
    if request.method == "POST":
        id = request.POST['address_id']
        currentUrl = request.POST['currentUrl']
        form = add_address(request.POST, instance=address.objects.get(id=id))
        if form.is_valid():
            form.save()
            return redirect(currentUrl)
    else:
        id = request.GET['address_id']
        currentUrl = request.GET['currentUrl']
        form = add_address(instance=address.objects.get(id=id))

    context = {
        'url': '/editaddress',
        'form': form,
        'address_id': id,
        'currentUrl': currentUrl,
        'session': foundUser(request),
        'whishlist_count': GetCountWhishlist(request)
    }
    return render(request, 'userTempl/register.html', context)



# =============================================================================
# invoice page. render this page after payment with the details product purchased

@never_cache
def Invoice(request, limit):
    OrderData = order.objects.filter(
        userId__username=request.session['user']).order_by('-date')[:int(limit)].values(
        'address', 'order_status', 'date', 'order_id',
        'variant_id__product_id__brand_id__brand_name', 'variant_id__product_id__product_name',
        'variant_id__variant', 'subtotal', 'total_qty', 'payment_method')

    data = OrderData[0]
    total = OrderData.aggregate(Sum('subtotal'))
    context = {
        'order': OrderData,
        'oneorder': data,
        'total': total,
        'category': Category.objects.all(),
        'session': foundUser(request),
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'whishlist_count': GetCountWhishlist(request)
    }
    return render(request, 'userTempl/invoice.html', context)



# =============================================================================
# delte user address. profile side address delete option and delete option in chekout have same view

def DelAddressFromCheckout(request):
    id = request.GET['address_id']
    address.objects.filter(id=id).delete()
    return JsonResponse({'success': True},safe=False)



# =============================================================================
# sort by popularity, low-to-high and high-to-low in the product list page

@never_cache
def SortBy(request):
    inp = request.GET.get('sortby', None)
    v = []

    if inp == 'popularity':
        o = order.objects.exclude(variant_id=None).values('variant_id').annotate(
            c=Sum('total_qty')).order_by('-c')
        for i in o:
            v += [VariantAndPrice.objects.get(id=i['variant_id'])]
    elif inp == 'low-high':
        v = VariantAndPrice.objects.select_related(
            'product_id').order_by('final_price')
    elif inp == 'high-low':
        v = VariantAndPrice.objects.select_related(
            'product_id').order_by('-final_price')

    paginator = Paginator(v, 6)
    page = request.GET.get('page')
    pageUrl = request.build_absolute_uri().replace('page='+str(page), '')
    try:
        a = paginator.page(page)
    except PageNotAnInteger:
        a = paginator.page(1)
    except EmptyPage:
        a = paginator.page(paginator.num_pages)

    context = {
        'allProducts': a,
        'brand': SubCategory.objects.all(),
        'ram': VariantAndPrice.objects.values("variant").distinct(),
        'category': Category.objects.all(),
        'session': foundUser(request),
        'cart_count': countItems(request),
        'pageUrl': pageUrl,
        'minBool': True,
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'whishlist_count': GetCountWhishlist(request)
    }

    return render(request, 'userTempl/product-grids.html', context)



# =============================================================================
# checking coupen is exist and if the user is used the coupen.

def AddCoupen(request):
    choosen = request.POST.get('choosen' or None)
    code = request.POST['coupen-code']
    err = 'fails'

    if Coupen.objects.filter(coupen_code=code).exists(): #check coupen exist in coupen table
        err = 'success'
        coupen = Coupen.objects.get(coupen_code=code)

        # checking if user already used this coupen . if user used coupen id is presented in order table  
        if not order.objects.filter(Q(coupen_id=coupen) & Q(userId=CustomUser.objects.get(username=request.session['user']))).exists():

            if VariantAndPrice.objects.filter(id=choosen).exists(): # if user id found in variant user selected buy now option

                v = VariantAndPrice.objects.get(id=choosen)
                finalPrice = v.final_price - \
                    (v.final_price * coupen.coupen_offer) / 100

            else: # user going buy product from cart

                val = FindSubTotal(request)
                finalPrice = val - (val * coupen.coupen_offer) / 100

            request.session['raz_amt'] = finalPrice * 100 # save the amt for razorpay payment

            return JsonResponse(
                {
                    'success': True,
                    'err': err,
                    'finalprice': finalPrice,
                    'offerIs': coupen.coupen_offer,
                    'coupenId': coupen.id,
                    # 'data-order_id': ordersid

                }, safe=False)

    return JsonResponse({'success': False, 'err': 'coupen code not found'},
                        safe=False)

# changing variant price and quantity according to user click on the variant in the each variant
def ChangeVariant(request):
    variantId = request.GET['variantId']
    vId = VariantAndPrice.objects.get(id=variantId)
    return JsonResponse(
        {
            'success': True,
            'pfinalprice': vId.final_price,
            'price': vId.price,
            'currentQuantity': vId.quantity,
            'currentRam': vId.variant
        },
        safe=False
    )



# =============================================================================
# order deials view

@never_cache
def Ordersdetials(request):
    order_data = order.objects.filter(
        userId__username=request.session['user']
    ).values(
        'userId__username',
        'date',
        'order_status',
        'subtotal',
        'variant_id__variant',
        'variant_id__product_id__product_name',
        'variant_id__product_id__brand_id__brand_name',
        'address',
        'payment_method',
        'total_qty',
        'variant_id__product_id__img1',
        'id'
    ).order_by('-date')

    paginator = Paginator(order_data, 10)
    page = request.GET.get('page')
    try:
        a = paginator.page(page)
    except PageNotAnInteger:
        a = paginator.page(1)
    except EmptyPage:
        a = paginator.page(paginator.num_pages)

    context = {
        'orderdetials': a,
        'ram': VariantAndPrice.objects.values("variant").distinct(),
        'category': Category.objects.all(),
        'brand': SubCategory.objects.all(),
        'session': foundUser(request),
        'cart_count': countItems(request),
        'page': page,
        'whishlist_count': GetCountWhishlist(request)
    }
    return render(request, 'userTempl/orders.html', context)



# =============================================================================
# amount for product is pas to razorpay when using click checkout option

def RazorpaySetAmt(request):
    raz_amt = request.session['raz_amt']

    DATA = {
        "amount": raz_amt,
        "currency": "INR",
        "receipt": "receipt#1",
        "notes": {
            "key1": "value3",
            "key2": "value2"
        }
    }
    orders = client.order.create(data=DATA)
    ordersid = orders['id']
    return JsonResponse({'status': 'success', 'ordersid': ordersid})



# =============================================================================
# adding product to whishlist

def AddToWhishlist(request):
    status = False
    count = None
    if 'user'  in request.session:
        whishlist.objects.update_or_create(
            product_variant=VariantAndPrice.objects.get(id=request.GET['vari_id']),user_id=CustomUser.objects.get(username=request.session['user'])
        )
        status = True
        count = whishlist.objects.filter(
            user_id__username=request.session['user']).count()
    return JsonResponse({'status': status, 'whishlist_count': count})


# =============================================================================
# whishlist page view

def Whishlist(request):
    if not 'user' in request.session:
        return redirect('/login')
    items = whishlist.objects.filter(user_id__username=request.session['user'])

    context = {
        'session': foundUser(request),
        'category': GetCategory(),
        'cart_count': countItems(request),
        'subcat': SubCategory.objects.values('id', 'c_id__id', 'c_id__id', 'brand_name'),
        'items': items,
        'whishlist_count': GetCountWhishlist(request),
        'minBool': True,
        'whishlist_count': GetCountWhishlist(request)

    }

    return render(request, 'userTempl/whishlist.html', context)


# =============================================================================
# remove product from wishlist

def RemoveFromWhishlist(request):
    whishlist.objects.filter(id=request.GET['vari_id']).delete()
    return JsonResponse({'status': True,'whishlist_count':  whishlist.objects.filter(
        user_id__username=request.session['user']).count()})



# =============================================================================
# resend otp  view

def ResendOtp(request):
    try:
        SendOTP("+91"+request.GET['num'])
    except:
        pass
    return JsonResponse({'status': True,})